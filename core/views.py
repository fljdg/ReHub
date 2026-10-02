import calendar as pycalendar
import os
from datetime import date, timedelta
from functools import wraps
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse

from . import services
from .models import Milestone, Proposal
from .search import run_search


# ---------------------------------------------------------------
# PUBLIC / MARKETING PAGES
# ---------------------------------------------------------------

def _handle_feedback(request):
    """Handles the footer feedback form (it posts to the home page)."""
    text = request.POST.get('feedback', '').strip()

    def flash(ok, message):
        # Kept in the session and picked up by the next home page load as
        # `feedback_message` / `feedback_ok` in the template context.
        request.session['feedback_status'] = {'ok': ok, 'message': message}

    if not text:
        flash(False, 'Please write your feedback before sending.')
    elif len(text) > 2000:
        flash(False, 'Your feedback is too long (2000 characters max).')
    else:
        sender = 'a visitor'
        if request.user.is_authenticated:
            sender = f'{request.user.username} <{request.user.email}>'
        recipient = os.getenv('FEEDBACK_EMAIL', 'rehub@example.com')
        try:
            send_mail(
                subject='ReHub feedback',
                message=f'From: {sender}\n\n{text}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception:
            flash(False, 'Sorry, we could not send your feedback. Please try again.')
        else:
            flash(True, 'Thank you! Your feedback has been sent.')

    return redirect(f"{request.path}#contact")


def home(request):
    """Renders the ReHub landing page (Home)."""
    if request.method == 'POST':
        return _handle_feedback(request)

    status = request.session.pop('feedback_status', None)
    context = {
        'feedback_message': status['message'] if status else None,
        'feedback_ok': status['ok'] if status else None,
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
        # The login box is still named "username" in the template, but people sign up
        # with an email, so an email typed there is what we look up. A plain username
        # (for example an admin account made with createsuperuser) still works too.
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = None
        if '@' in identifier:
            for candidate in User.objects.filter(email__iexact=identifier):
                user = authenticate(request, username=candidate.get_username(), password=password)
                if user is not None:
                    break
        else:
            user = authenticate(request, username=identifier, password=password)

        if user is not None:
            login(request, user)
            if request.POST.get('remember'):
                request.session.set_expiry(60 * 60 * 24 * 30)  # stay signed in for 30 days
            else:
                request.session.set_expiry(0)  # sign out when the browser closes
            return redirect('core:dashboard')
        error = 'Incorrect email or password.'
    return render(request, 'core/login.html', {'error': error})


def signup_view(request):
    """Creates a real auth.User account (this was a no-op stub before)."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    errors = []
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not all([first_name, last_name, email, password1, password2]):
            errors.append('Please fill in every field.')
        if password1 and password2 and password1 != password2:
            errors.append('Passwords do not match.')
        if password1 and password1 == password2:
            # Django's real validators: length, too common, all numeric, too similar to name/email.
            try:
                validate_password(
                    password1,
                    user=User(email=email, first_name=first_name, last_name=last_name,
                              username=email.split('@')[0]),
                )
            except ValidationError as exc:
                errors.extend(exc.messages)
        if email and User.objects.filter(email__iexact=email).exists():
            errors.append('An account with that email already exists.')
        if not request.POST.get('terms'):
            errors.append('Please accept the Terms and Conditions.')

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
# AUTHENTICATED APP PAGES
# ---------------------------------------------------------------

def _profile_context(user):
    """Small helper so every authenticated page gets the same nav/header data."""
    display_name = user.get_full_name() or user.username
    role = 'Evaluator' if services.user_is_evaluator_anywhere(user) else 'Student'
    initials = ''.join(part[0] for part in display_name.split()[:2]).upper() or user.username[:2].upper()
    return {'display_name': display_name, 'role': role, 'initials': initials}


def _search_redirect(view):
    """The top search bar in the designed pages submits to the page you are on (?q=...).
    This sends that search to the results page, so those templates need no changes."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.method == 'GET' and 'q' in request.GET:
            return redirect(f"{reverse('core:search')}?{urlencode({'q': request.GET['q']})}")
        return view(request, *args, **kwargs)
    return wrapper


@login_required
@_search_redirect
def dashboard(request):
    """Home page shown right after login (the nav's 'Home' tab)."""
    context = _profile_context(request.user)
    stats = services.dashboard_stats(request.user)
    context['stats'] = stats
    context['proposal_count'] = stats['total']
    context['pending_count'] = stats['waiting']
    context['approved_count'] = stats['approved']
    context['revision_count'] = stats['returned']
    context['recent_proposals'] = stats['cards'][:5]
    context['review_queue'] = stats['review_queue'][:6]
    context['needs_group'] = stats['needs_group']
    return render(request, 'core/dashboard.html', context)


@login_required
@_search_redirect
def research(request):
    """The 'My Research' tab: list your proposals, submit a new one."""
    context = _profile_context(request.user)
    errors = []

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        uploaded_file = request.FILES.get('file')

        if not title:
            errors.append('Please give your proposal a title.')
        if not description:
            errors.append('Please add a description.')

        if not errors:
            Proposal.objects.create(
                title=title,
                description=description,
                file=uploaded_file,
                submitted_by=request.user,
            )
            return redirect('core:research')

    context['errors'] = errors
    context['proposals'] = Proposal.objects.filter(submitted_by=request.user).order_by('-created_at')
    return render(request, 'core/myResearch.html', context)


@login_required
@_search_redirect
def assistant(request):
    """The 'AI Assistant' tab."""
    context = _profile_context(request.user)
    return render(request, 'core/assistant.html', context)


@login_required
@_search_redirect
def calendar_view(request):
    """The 'Calendar' tab: a month grid of your chapter due dates (?month=YYYY-MM)."""
    context = _profile_context(request.user)
    today = date.today()

    try:
        year, month = (int(part) for part in request.GET.get('month', '').split('-'))
        first = date(year, month, 1)
    except ValueError:
        first = today.replace(day=1)

    weeks = pycalendar.Calendar(firstweekday=6).monthdatescalendar(first.year, first.month)
    by_day = {}
    for item in services.calendar_items(request.user, weeks[0][0], weeks[-1][-1], today):
        by_day.setdefault(item.due_date, []).append(item)

    context['month_label'] = first.strftime('%B %Y')
    context['prev_month'] = (first - timedelta(days=1)).strftime('%Y-%m')
    context['next_month'] = (first + timedelta(days=32)).strftime('%Y-%m')
    context['weekdays'] = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    context['weeks'] = [
        [
            {
                'date': day,
                'in_month': day.month == first.month,
                'is_today': day == today,
                'events': by_day.get(day, []),
            }
            for day in week
        ]
        for week in weeks
    ]
    context['upcoming'] = services.upcoming_items(request.user, today)
    return render(request, 'core/calendar.html', context)


@login_required
@_search_redirect
def profile(request):
    """The 'Me' tab."""
    context = _profile_context(request.user)
    context['proposal_count'] = Proposal.objects.filter(submitted_by=request.user).count()
    context['recent_proposals'] = (
        Proposal.objects.filter(submitted_by=request.user).order_by('-created_at')[:5]
    )
    return render(request, 'core/profile.html', context)


@login_required
def search(request):
    """Results page for the top search bar (temporary UI in core/templates/core/temp/)."""
    query = request.GET.get('q', '').strip()[:100]
    context = _profile_context(request.user)
    context['q'] = query
    context['results'] = run_search(request.user, query) if query else None
    return render(request, 'core/temp/search.html', context)