from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .models import StudyGroup
from .profile_views import _image_ok
from .views import _profile_context, _search_redirect


def member_label(user):
    return user.get_full_name() or user.username


@login_required
@_search_redirect
def groups(request):
    """Group tab: grid of group cards, add-group dialog, filter menu."""
    context = _profile_context(request.user)
    errors = []

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()[:120]
        image = request.FILES.get('image')
        usernames = [u.strip() for u in request.POST.get('members', '').replace('\n', ',').split(',') if u.strip()]

        if not name:
            errors.append('Please give your group a name.')
        if image:
            _image_ok(image, 'Group image', errors)

        found = list(User.objects.filter(username__in=usernames))
        known = {u.username.lower() for u in found}
        missing = [u for u in usernames if u.lower() not in known]
        if missing:
            errors.append('No account found for: ' + ', '.join(missing) + '.')

        if not errors:
            group = StudyGroup.objects.create(name=name, created_by=request.user)
            if image:
                group.image = image
                group.save()
            group.members.add(request.user, *found)
            return redirect('core:group')

    show = request.GET.get('show', 'all')
    sort = request.GET.get('sort', 'newest')
    queryset = StudyGroup.objects.prefetch_related('members')
    if show == 'mine':
        queryset = queryset.filter(members=request.user)
    queryset = queryset.order_by('name' if sort == 'name' else '-created_at')

    context['errors'] = errors
    context['show'] = show
    context['sort'] = sort
    context['cards'] = [
        {'group': g, 'names': ', '.join(member_label(m) for m in g.members.all())}
        for g in queryset
    ]
    context['active_nav'] = 'group'
    return render(request, 'core/group.html', context)
