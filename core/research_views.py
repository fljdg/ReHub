import calendar as pycalendar
from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import ChapterSubmission, Proposal
from .views import _profile_context, _search_redirect


def _project(proposal):
    # Reverse one-to-one raises AttributeError when there is no project yet.
    return getattr(proposal, 'project', None)


def _percent(proposal):
    project = _project(proposal)
    total = project.milestones.count() if project else 0
    if not total:
        return 0
    return round(project.milestones.filter(status='done').count() * 100 / total)


@login_required
@_search_redirect
def research(request):
    """My Research: list of your research cards + the add-proposal dialog."""
    context = _profile_context(request.user)
    errors = []

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        if not title:
            errors.append('Please give your proposal a title.')
        if not description:
            errors.append('Please add a description.')
        if not errors:
            Proposal.objects.create(
                title=title,
                description=description,
                file=request.FILES.get('file'),
                submitted_by=request.user,
            )
            return redirect('core:research')

    proposals = Proposal.objects.filter(submitted_by=request.user).order_by('-created_at')
    context['errors'] = errors
    context['rows'] = [{'proposal': p, 'percent': _percent(p)} for p in proposals]
    return render(request, 'core/myResearch.html', context)


@login_required
@_search_redirect
def research_detail(request, pk):
    """One research: upload per tab (Proposal, Chapter 1-3), feedback, deadlines."""
    proposal = get_object_or_404(Proposal, pk=pk, submitted_by=request.user)
    context = _profile_context(request.user)
    errors = []
    active = 0

    try:
        active = min(max(int(request.GET.get('tab', 0)), 0), 3)
    except ValueError:
        pass

    if request.method == 'POST':
        try:
            active = min(max(int(request.POST.get('chapter', 0)), 0), 3)
        except ValueError:
            active = 0
        uploaded = request.FILES.get('file')
        if not uploaded:
            errors.append('Choose a file before you turn in.')
        elif active == 0:
            proposal.file = uploaded
            proposal.status = 'pending'
            proposal.save()
        else:
            ChapterSubmission.objects.update_or_create(
                proposal=proposal, chapter=active,
                defaults={'file': uploaded, 'status': 'pending'},
            )
        if not errors:
            return redirect(f"{reverse('core:research_detail', args=[pk])}?tab={active}")

    tag = {'approved': 'green', 'rejected': 'red'}
    subs = {c.chapter: c for c in proposal.chapters.all()}
    tabs = [{
        'n': 0, 'label': 'Proposal', 'prompt': 'Upload your proposal here',
        'file': proposal.file or None, 'status': proposal.get_status_display(),
        'tag': tag.get(proposal.status, 'amber'), 'feedback': '',
    }]
    for n in (1, 2, 3):
        sub = subs.get(n)
        tabs.append({
            'n': n, 'label': f'Chapter {n}', 'prompt': f'Upload your Chapter {n}',
            'file': sub.file if sub else None,
            'status': sub.get_status_display() if sub else '',
            'tag': tag.get(sub.status, 'amber') if sub else '',
            'feedback': sub.feedback if sub else '',
        })

    project = _project(proposal)
    milestones = list(project.milestones.order_by('due_date')) if project else []
    open_ones = [m for m in milestones if m.status != 'done']
    in_progress = [m for m in milestones if m.status == 'in_progress']
    current = (in_progress or open_ones or milestones[-1:] or [None])[0]

    today = date.today()
    context.update({
        'proposal': proposal,
        'percent': _percent(proposal),
        'errors': errors,
        'tabs': tabs,
        'active': active,
        'evaluations': proposal.evaluations.order_by('-evaluated_at'),
        'next_deadline': open_ones[0] if open_ones else None,
        'current_milestone': current,
        'today': today,
        'month_label': today.strftime('%B %Y'),
        'weeks': pycalendar.Calendar(firstweekday=6).monthdatescalendar(today.year, today.month),
        'due_days': {m.due_date for m in open_ones},
    })
    return render(request, 'core/researchDetail.html', context)
