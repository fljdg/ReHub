"""Email one-time passcode (OTP) for creating an account.

Flow: the sign-up form is validated first. If it is fine, NO account is created yet.
The details are parked in the session and a 6-digit code is emailed. The account is
only created once that code is typed on the verify page, which proves the person
owns the email address.

The password is stored in the session already hashed, and only a keyed hash of the
code is kept, never the code itself. Functions take the session as a plain mapping
so they are easy to test.
"""
import hashlib
import hmac
import secrets
import time

from django.conf import settings
from django.core.mail import send_mail

SESSION_KEY = 'signup_otp'
MAX_SENDS = 5          # first email + resends, per sign-up attempt


class OTPConfigError(Exception):
    """Email is not set up on this server, so a code could not be delivered."""


def _digest(code, email):
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, f'{email.lower()}:{code}'.encode(), hashlib.sha256).hexdigest()


def enabled():
    return getattr(settings, 'OTP_ENABLED', True)


def mask_email(email):
    name, _, domain = email.partition('@')
    if not domain:
        return email
    return f"{name[:1]}{'*' * max(len(name) - 1, 2)}@{domain}"


def pending(session):
    return session.get(SESSION_KEY)


def clear(session):
    session.pop(SESSION_KEY, None)


def seconds_until_resend(state, now=None):
    now = now if now is not None else time.time()
    wait = getattr(settings, 'OTP_RESEND_SECONDS', 60)
    return max(0, int(state['sent'] + wait - now + 0.999))


def _new_code():
    length = getattr(settings, 'OTP_LENGTH', 6)
    return ''.join(secrets.choice('0123456789') for _ in range(length))


def issue(session, signup, now=None, sends=0):
    """Create a fresh code and park the sign-up in the session. Returns the plain code.

    `signup` is a dict with first_name, last_name, email and password_hash.
    """
    now = now if now is not None else time.time()
    code = _new_code()
    session[SESSION_KEY] = {
        'signup': signup,
        'hash': _digest(code, signup['email']),
        'exp': now + getattr(settings, 'OTP_TTL_MINUTES', 10) * 60,
        'tries': 0,
        'sent': now,
        'sends': sends + 1,
    }
    return code


def verify(session, code, now=None):
    """Check a typed code. Returns (ok, reason, state).

    reason is None on success, else 'none' (nothing pending), 'expired',
    'locked' (too many wrong tries) or 'wrong'.
    """
    now = now if now is not None else time.time()
    state = session.get(SESSION_KEY)
    if not state:
        return False, 'none', None
    if now > state['exp']:
        clear(session)
        return False, 'expired', None
    if hmac.compare_digest(state['hash'], _digest(code or '', state['signup']['email'])):
        clear(session)
        return True, None, state
    state['tries'] += 1
    if state['tries'] >= getattr(settings, 'OTP_MAX_ATTEMPTS', 5):
        clear(session)
        return False, 'locked', None
    session[SESSION_KEY] = state          # reassign so the session saves the new count
    return False, 'wrong', state


def send_code(signup, code):
    """Email the code. Raises OTPConfigError / the mail error if it cannot be sent."""
    on_console = settings.EMAIL_BACKEND.endswith('console.EmailBackend')
    if on_console and not settings.DEBUG:
        raise OTPConfigError('Email is not configured on the server.')
    minutes = getattr(settings, 'OTP_TTL_MINUTES', 10)
    send_mail(
        subject=f'{code} is your ReHub verification code',
        message=(
            f"Hi {signup['first_name']},\n\n"
            f'Welcome to ReHub! Your verification code is: {code}\n\n'
            f'Enter it on the sign-up page to finish creating your account. '
            f'It expires in {minutes} minutes. If you did not sign up, ignore this email.\n\n'
            f'- ReHub'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[signup['email']],
        fail_silently=False,
    )


def begin(session, signup):
    """Start verification: issue + email a code. Raises if the email cannot be sent."""
    code = issue(session, signup)
    try:
        send_code(signup, code)
    except Exception:
        clear(session)
        raise
