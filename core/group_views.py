import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .models import GroupMember, Proposal
from .profile_views import _image_ok
from .services import ServiceError
from .views import _profile_context, _search_redirect


def member_label(user):
    return user.get_full_name() or user.username


def _emails(raw):
    seen, out = set(), []
    for e in re.split(r'[,;\s]+', raw or ''):
        e = e.strip()
        if e and e.lower() not in seen:
            seen.add(e.lower())
            out.append(e)
    return out


@login_required
@_search_redirect
def groups(request):
    """Group tab: MY groups, pending invites, and the add-group dialog."""
    context = _profile_context(request.user)
    errors = []

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()[:120]
        image = request.FILES.get('image')
        emails = _emails(request.POST.get('emails', ''))
        if image:
            _image_ok(image, 'Group image', errors)
        if not errors:
            try:
                group, problems = services.create_group(request.user, name, image, emails)
            except ServiceError as e:
                errors.append(str(e))
            else:
                for p in problems:
                    messages.warning(request, 'Invite not sent - ' + p)
                return redirect('core:group_detail', pk=group.pk)

    sort = request.GET.get('sort', 'newest')
    queryset = services.my_groups(request.user).prefetch_related('memberships__user')
    queryset = queryset.order_by('name' if sort == 'name' else '-created_at')

    cards = []
    for g in queryset:
        active = [m for m in g.memberships.all() if m.status == 'active']
        cards.append({'group': g, 'names': ', '.join(member_label(m.user) for m in active)})

    context['errors'] = errors
    context['sort'] = sort
    context['cards'] = cards
    context['invites'] = services.pending_invites(request.user)
    context['active_nav'] = 'group'
    return render(request, 'core/group.html', context)


@login_required
@_search_redirect
def group_detail(request, pk):
    group = services.get_group_or_404(request.user, pk)
    me_evaluator = services.is_evaluator(request.user, group)
    memberships = list(group.memberships.select_related('user').all())
    active = [m for m in memberships if m.status == 'active']
    active.sort(key=lambda m: (m.role != 'evaluator', member_label(m.user).lower()))
    waiting = [m for m in memberships if m.status in ('invited', 'declined')] if me_evaluator else []

    research = Proposal.objects.filter(group=group).first()
    context = _profile_context(request.user)
    context.update({
        'group': group,
        'is_evaluator': me_evaluator,
        'members': [{'m': m, 'label': member_label(m.user)} for m in active],
        'waiting': [{'m': m, 'label': member_label(m.user)} for m in waiting],
        'research': research,
        'progress': services.progress_percent(research) if research else 0,
        'active_nav': 'group',
    })
    return render(request, 'core/group_detail.html', context)


@login_required
@require_POST
def group_invite(request, pk):
    group = services.get_group_or_404(request.user, pk)
    emails = _emails(request.POST.get('emails', ''))
    if not emails:
        messages.error(request, 'Enter at least one email.')
    for email in emails:
        try:
            services.invite(group, request.user, email)
            messages.success(request, f'Invite sent to {email}.')
        except ServiceError as e:
            messages.error(request, f'{email}: {e}')
    return redirect('core:group_detail', pk=group.pk)


def _respond(request, mpk, accept):
    membership = get_object_or_404(GroupMember, pk=mpk, user=request.user)
    try:
        services.respond_invite(membership, request.user, accept)
    except ServiceError as e:
        messages.error(request, str(e))
        return redirect('core:group')
    if accept:
        return redirect('core:group_detail', pk=membership.group_id)
    return redirect('core:group')


@login_required
@require_POST
def invite_accept(request, mpk):
    return _respond(request, mpk, True)


@login_required
@require_POST
def invite_decline(request, mpk):
    return _respond(request, mpk, False)


@login_required
@require_POST
def member_remove(request, pk, mpk):
    group = services.get_group_or_404(request.user, pk)
    membership = get_object_or_404(GroupMember, pk=mpk, group=group)
    try:
        services.remove_member(group, request.user, membership)
        messages.success(request, 'Member removed.')
    except ServiceError as e:
        messages.error(request, str(e))
    return redirect('core:group_detail', pk=group.pk)


@login_required
@require_POST
def group_leave(request, pk):
    group = services.get_group_or_404(request.user, pk)
    try:
        services.leave_group(group, request.user)
    except ServiceError as e:
        messages.error(request, str(e))
        return redirect('core:group_detail', pk=group.pk)
    return redirect('core:group')


@login_required
@require_POST
def research_new(request, pk):
    group = services.get_group_or_404(request.user, pk)
    try:
        services.start_research(
            group, request.user,
            request.POST.get('title', ''), request.POST.get('description', ''),
            request.FILES.get('file'))
        messages.success(request, 'Proposal uploaded. Your evaluator can now review it.')
    except ServiceError as e:
        messages.error(request, str(e))
    return redirect('core:group_detail', pk=group.pk)