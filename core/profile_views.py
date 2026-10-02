import os

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from . import services, views
from .models import Profile, Proposal
from .views import _profile_context, _search_redirect

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_IMAGE_MB = 5


def _image_ok(upload, label, errors):
    ext = os.path.splitext(upload.name)[1].lower()
    if ext not in IMAGE_EXTS:
        errors.append(f'{label} must be a JPG, PNG, GIF or WEBP image.')
    elif upload.size > MAX_IMAGE_MB * 1024 * 1024:
        errors.append(f'{label} must be {MAX_IMAGE_MB} MB or smaller.')
    else:
        return True
    return False


def signup(request):
    """Same sign-up as before, but a brand-new account goes straight to profile setup."""
    response = views.signup_view(request)
    if request.method == 'POST' and request.user.is_authenticated and response.status_code == 302:
        return redirect('core:setup_profile')
    return response


@login_required
def setup_profile(request):
    """First screen after Get Started: photo + program/department."""
    profile, _ = Profile.objects.get_or_create(user=request.user)
    errors = []

    if request.method == 'POST':
        program = request.POST.get('program', '').strip()[:150]
        avatar = request.FILES.get('avatar')
        if not program:
            errors.append('Please enter your program or department.')
        if avatar:
            _image_ok(avatar, 'Profile photo', errors)
        if not errors:
            profile.program = program
            if avatar:
                profile.avatar = avatar
            profile.save()
            return redirect('core:dashboard')

    context = _profile_context(request.user)
    context.update({'profile': profile, 'errors': errors, 'active_nav': 'none'})
    return render(request, 'core/setupProfile.html', context)


@login_required
@_search_redirect
def profile(request):
    """The 'Me' tab, with working edit (name, bio, program, photo, cover)."""
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    errors = []

    if request.method == 'POST':
        first = request.POST.get('first_name', '').strip()[:150]
        last = request.POST.get('last_name', '').strip()[:150]
        avatar = request.FILES.get('avatar')
        banner = request.FILES.get('banner')
        if not first:
            errors.append('Please enter your first name.')
        if avatar:
            _image_ok(avatar, 'Profile photo', errors)
        if banner:
            _image_ok(banner, 'Cover photo', errors)
        if not errors:
            user.first_name, user.last_name = first, last
            user.save(update_fields=['first_name', 'last_name'])
            profile.program = request.POST.get('program', '').strip()[:150]
            profile.bio = request.POST.get('bio', '').strip()[:300]
            if avatar:
                profile.avatar = avatar
            if banner:
                profile.banner = banner
            profile.save()
            return redirect('core:profile')

    cards = services.research_cards(user)
    context = _profile_context(user)
    context.update({
        'profile': profile,
        'errors': errors,
        'proposal_count': len(cards),
        'recent_proposals': cards[:5],
    })
    return render(request, 'core/profile.html', context)