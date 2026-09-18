from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.shortcuts import redirect, render

from .models import Proposal


# ---------------------------------------------------------------
# PUBLIC / MARKETING PAGES
# ---------------------------------------------------------------

def home(request):
    """Renders the ReHub landing page (Home)."""
    context = {
        'features': [
            {
                'title': 'Proposal Management',
                'text': 'For students and faculty to submit, track, review, revise, and approve research proposals securely.',
            },
            {
                'title': 'AI Research Assistant',
                'text': 'To improve proposals, recommends relevant research, and detects duplicate topics.',
            },
            {
                'title': 'Planning & Milestones',
                'text': 'Built-in tools for setting weekly milestones, assigning tasks, and tracking project timelines.',
            },
        ],
        'steps': [
            {
                'number': 'Step 1:',
                'title': 'Submit Proposal',
                'text': 'Upload documents & details',
            },
            {
                'number': 'Step 2:',
                'title': 'AI & Panel Review',
                'text': 'Receive AI tips and evaluator feedback',
            },
            {
                'number': 'Step 3:',
                'title': 'Track & Complete',
                'text': 'Manage milestones and monitor progress to the finish line',
            },
        ],
        'team': [
            {'name': 'Leala Vieann Rivera', 'role': 'Evaluator I'},
            {'name': 'Renher Jethro Silva', 'role': 'Evaluator II'},
            {'name': 'Nick Angelo Tolentino', 'role': 'Evaluator III'},
            {'name': 'Vergil Del Monte', 'role': 'Research Adviser'},
        ],
    }
    return render(request, 'core/home.html', context)


# ---------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('core:dashboard')
        error = 'Incorrect username or password.'
    return render(request, 'core/login.html', {'error': error})


def signup_view(request):
    """Creates a real auth.User account (this was a no-op stub before)."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    errors = []
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not all([first_name, last_name, email, password1, password2]):
            errors.append('Please fill in every field.')
        if password1 and password2 and password1 != password2:
            errors.append('Passwords do not match.')
        if password1 and len(password1) < 8:
            errors.append('Password must be at least 8 characters.')
        if email and User.objects.filter(email__iexact=email).exists():
            errors.append('An account with that email already exists.')

        if not errors:
            username = email.split('@')[0]
            candidate = username
            suffix = 1
            while User.objects.filter(username=candidate).exists():
                candidate = f'{username}{suffix}'
                suffix += 1

            try:
                user = User.objects.create_user(
                    username=candidate,
                    email=email,
                    password=password1,
                    first_name=first_name,
                    last_name=last_name,
                )
            except IntegrityError:
                errors.append('Could not create your account. Please try again.')
            else:
                login(request, user)
                return redirect('core:dashboard')

    return render(request, 'core/signup.html', {'errors': errors})


def logout_view(request):
    logout(request)
    return redirect('core:home')


# ---------------------------------------------------------------
# DASHBOARD (auth required)
# ---------------------------------------------------------------

def _profile_context(user):
    """Small helper so every dashboard page gets the same header/sidebar data."""
    display_name = user.get_full_name() or user.username
    if user.is_superuser:
        role = 'Administrator'
    elif user.is_staff:
        role = 'Staff'
    else:
        role = 'Student'
    initials = ''.join(part[0] for part in display_name.split()[:2]).upper() or user.username[:2].upper()
    return {'display_name': display_name, 'role': role, 'initials': initials}


@login_required
def dashboard(request):
    context = _profile_context(request.user)
    context['proposal_count'] = Proposal.objects.filter(submitted_by=request.user).count()
    context['recent_proposals'] = (
        Proposal.objects.filter(submitted_by=request.user).order_by('-created_at')[:5]
    )
    return render(request, 'core/dashboard.html', context)
