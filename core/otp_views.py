import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import otp

PROBLEMS = {
    'none': 'Your sign-up session expired. Please fill in the sign-up form again.',
    'expired': 'That code expired. Please sign up again to get a new one.',
    'locked': 'Too many wrong codes. Please sign up again to get a new one.',
    'taken': 'An account with that email already exists. Try logging in instead.',
}


def _create_account(signup):
    """Makes the real account once the email is proven. Returns the new User."""
    base = signup['email'].split('@')[0]
    username = base
    suffix = 1
    while User.objects.filter(username=username).exists():
        username = f'{base}{suffix}'
        suffix += 1
    user = User(
        username=username,
        email=signup['email'],
        first_name=signup['first_name'],
        last_name=signup['last_name'],
        password=signup['password_hash'],     # already hashed, set as-is
    )
    user.save()
    return user


def verify_otp(request):
    """Step 2 of sign-up: type the code that was emailed, then the account is created."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    state = otp.pending(request.session)
    if state is None:
        return redirect('core:signup')
    signup = state['signup']

    error = None
    if request.method == 'POST':
        code = re.sub(r'\D', '', request.POST.get('code', ''))
        ok, reason, done = otp.verify(request.session, code)
        if ok:
            try:
                if User.objects.filter(email__iexact=signup['email']).exists():
                    raise IntegrityError('email taken')
                user = _create_account(done['signup'])
            except IntegrityError:
                return render(request, 'core/verify_otp.html', {'dead_end': PROBLEMS['taken']})
            login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
            return redirect('core:setup_profile')
        if reason == 'wrong':
            error = 'That code is not right. Check the email and try again.'
        else:
            return render(request, 'core/verify_otp.html', {'dead_end': PROBLEMS[reason]})
        state = otp.pending(request.session)

    return render(request, 'core/verify_otp.html', {
        'error': error,
        'masked_email': otp.mask_email(signup['email']),
        'wait': otp.seconds_until_resend(state),
        'otp_length': getattr(settings, 'OTP_LENGTH', 6),
    })


@require_POST
def resend_otp(request):
    state = otp.pending(request.session)
    if state is None:
        return redirect('core:signup')

    if state['sends'] >= otp.MAX_SENDS:
        messages.error(request, 'Too many codes requested. Please try again later.')
    elif otp.seconds_until_resend(state):
        messages.error(request, 'Please wait a moment before asking for another code.')
    else:
        code = otp.issue(request.session, state['signup'], sends=state['sends'])
        try:
            otp.send_code(state['signup'], code)
        except Exception:
            messages.error(request, 'We could not send the email. Please try again.')
        else:
            messages.success(request, 'A new code was sent.')
    return redirect('core:verify_otp')
