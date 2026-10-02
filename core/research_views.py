import calendar as pycalendar
import mimetypes
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_POST

from . import services
from .models import Assignment, GroupMember, Proposal, Submission
from .services import ServiceError
from .views import _profile_context, _search_redirect

TAG = {'approved': 'green', 'rejected': 'red', 'pending': 'amber', 'empty': ''}
LABEL = {'approved': 'Approved', 'rejected': 'Rejected', 'pending': 'Waiting for review', 'empty': ''}


@login_required
@_search_redirect
def research(request):
    """My Research: one card per research project of the groups I'm in."""
    context = _profile_context(request.user)
    groups = services.my_groups(request.user)
    proposals = (Proposal.objects.filter(group__in=groups)
                 .select_related('group').prefetch_related('assignments__submissions')
                 .order_by('-created_at'))
    my_roles = dict(GroupMember.objects.filter(user=request.user, status='active')
                    .values_list('group_id', 'role'))
    rows = [{
        'proposal': p,
        'percent': services.progress_percent(p),
        'role': my_roles.get(p.group_id, 'member'),
    } for p in proposals]
    with_research = {p.group_id for p in proposals}
    context['rows'] = rows
    context['groups_without_research'] = [g for g in groups if g.pk not in with_research]
    context['needs_group'] = not groups.exists() and not services.pending_invites(request.user).exists()
    context['has_invites'] = services.pending_invites(request.user).exists()
    return render(request, 'core/myResearch.html', context)


def _build_tabs(proposal, user, group):
    me_student = services.is_student_member(user, group)
    me_eval = services.is_evaluator(user, group)
    assignments = list(proposal.assignments.prefetch_related('submissions__uploaded_by', 'submissions__reviewed_by'))
    tabs = []
    prev = None
    for a in assignments:
        subs = list(a.submissions.all())          # newest first
        latest = subs[0] if subs else None
        state = latest.status if latest else 'empty'
        unlocked = a.position == 0 or (prev is not None and prev['state'] == 'approved')
        can_upload = unlocked and state in ('empty', 'rejected')
        tab = {
            'a': a, 'n': a.position, 'label': a.title, 'state': state,
            'tag': TAG[state], 'status': LABEL[state],
            'unlocked': unlocked,
            'can_upload': me_student and can_upload,
            'locked_by': prev['label'] if prev and not unlocked else '',
            'latest': latest, 'history': subs[1:] if subs else [],
            'subs': subs,
            'prompt': 'Upload your proposal here' if a.kind == 'proposal' else f'Upload your {a.title}',
            'can_review': me_eval and latest is not None and state == 'pending',
        }
        tabs.append(tab)
        prev = tab
    if tabs:
        last_n = tabs[-1]['n']
        for t in tabs:
            t['can_delete'] = (me_eval and t['a'].kind == 'chapter'
                               and t['n'] == last_n and not t['subs'])
    return tabs


@login_required
@_search_redirect
def research_detail(request, pk):
    proposal = services.get_proposal_or_404(request.user, pk)
    group = proposal.group
    tabs = _build_tabs(proposal, request.user, group)

    # which tab opens: ?tab=<position>, else the first one that isn't approved yet
    active = None
    try:
        wanted = int(request.GET.get('tab', ''))
        if any(t['n'] == wanted for t in tabs):
            active = wanted
    except ValueError:
        pass
    if active is None:
        pending = [t for t in tabs if t['state'] != 'approved' and t['unlocked']]
        active = (pending[0] if pending else tabs[-1])['n'] if tabs else 0

    unfinished = [t for t in tabs if t['state'] != 'approved']
    current = unfinished[0] if unfinished else None
    with_dates = [t for t in unfinished if t['a'].due_date]
    next_deadline = with_dates[0] if with_dates else None

    today = timezone.localdate()
    context = _profile_context(request.user)
    context.update({
        'proposal': proposal, 'group': group,
        'is_evaluator': services.is_evaluator(request.user, group),
        'percent': services.progress_percent(proposal),
        'tabs': tabs, 'active': active,
        'plan_set': bool(proposal.plan_confirmed_at),
        'plan_ready': bool(tabs and tabs[0]['latest'] is not None and not proposal.plan_confirmed_at),
        'can_add_chapter': bool(proposal.plan_confirmed_at and len(tabs) - 1 < services.MAX_CHAPTERS),
        'min_deadline': (timezone.localdate() + timedelta(days=2)).isoformat(),
        'next_deadline': next_deadline, 'current': current,
        'today': today,
        'month_label': today.strftime('%B %Y'),
        'weeks': pycalendar.Calendar(firstweekday=6).monthdatescalendar(today.year, today.month),
        'due_days': {t['a'].due_date for t in unfinished if t['a'].due_date},
    })
    return render(request, 'core/researchDetail.html', context)


@login_required
@require_POST
def tab_submit(request, pk, apk):
    proposal = services.get_proposal_or_404(request.user, pk)
    assignment = get_object_or_404(Assignment, pk=apk, proposal=proposal)
    try:
        sub = services.submit(assignment, request.user, request.FILES.get('file'))
        messages.success(request, f'Uploaded as version {sub.version}. Waiting for your evaluator.')
    except ServiceError as e:
        messages.error(request, str(e))
    return redirect(f"{reverse('core:research_detail', args=[proposal.pk])}?tab={assignment.position}")


@login_required
@require_GET
@xframe_options_sameorigin          # lets the PDF preview iframe work on our own pages only
def submission_download(request, pk):
    sub = services.get_submission_or_404(request.user, pk)
    name = sub.original_name or sub.file.name.rsplit('/', 1)[-1]
    try:
        handle = sub.file.open('rb')
    except (FileNotFoundError, ValueError, OSError):
        raise Http404("This file isn't on this server (it may have been uploaded somewhere else).")
    content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    response = FileResponse(handle, content_type=content_type,
                            as_attachment=bool(request.GET.get('dl')), filename=name)
    response['X-Content-Type-Options'] = 'nosniff'
    return response


# ---------------------------------------------------------------- evaluator tools

def _back(proposal, position=0):
    return redirect(f"{reverse('core:research_detail', args=[proposal.pk])}?tab={position}")


def _parse_date(value):
    value = (value or '').strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise ServiceError("Enter a valid date.")


@login_required
@require_POST
def plan_setup(request, pk):
    proposal = services.get_proposal_or_404(request.user, pk)
    try:
        deadline = _parse_date(request.POST.get('deadline'))
        if deadline is None:
            raise ServiceError("Enter the final deadline.")
        titles = [t.strip() for t in request.POST.get('titles', '').splitlines()]
        services.confirm_plan(proposal, request.user, deadline,
                              request.POST.get('chapter_count'), titles)
        messages.success(request, 'Plan saved. The chapter tabs are ready.')
    except ServiceError as e:
        messages.error(request, str(e))
    return _back(proposal, 0)


@login_required
@require_POST
def tab_edit(request, pk, apk):
    proposal = services.get_proposal_or_404(request.user, pk)
    assignment = get_object_or_404(Assignment, pk=apk, proposal=proposal)
    try:
        services.rename_assignment(assignment, request.user, request.POST.get('title'))
        services.set_due_date(assignment, request.user, _parse_date(request.POST.get('due_date')))
        messages.success(request, 'Tab updated.')
    except ServiceError as e:
        messages.error(request, str(e))
    return _back(proposal, assignment.position)


@login_required
@require_POST
def tab_add(request, pk):
    proposal = services.get_proposal_or_404(request.user, pk)
    try:
        new = services.add_chapter(proposal, request.user, request.POST.get('title'))
        messages.success(request, f'Added "{new.title}".')
        return _back(proposal, new.position)
    except ServiceError as e:
        messages.error(request, str(e))
    return _back(proposal, 0)


@login_required
@require_POST
def tab_delete(request, pk, apk):
    proposal = services.get_proposal_or_404(request.user, pk)
    assignment = get_object_or_404(Assignment, pk=apk, proposal=proposal)
    try:
        services.delete_last_chapter(assignment, request.user)
        messages.success(request, 'Chapter deleted.')
        return _back(proposal, max(assignment.position - 1, 0))
    except ServiceError as e:
        messages.error(request, str(e))
    return _back(proposal, assignment.position)


@login_required
@require_POST
def submission_review(request, pk):
    sub = services.get_submission_or_404(request.user, pk)
    proposal = sub.assignment.proposal
    decision = request.POST.get('decision')
    try:
        services.review(sub, request.user, decision, request.POST.get('feedback', ''))
        if decision == 'approve':
            messages.success(request, 'Approved. The next tab is unlocked.')
        else:
            messages.success(request, 'Rejected. The members can upload a new version.')
    except ServiceError as e:
        messages.error(request, str(e))
    return _back(proposal, sub.assignment.position)