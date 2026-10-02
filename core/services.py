"""
All business rules for groups, research tabs, uploads and reviews.
Views should only call these functions and show the result.
Every rule failure raises ServiceError(message) -> views show the message to the user.
"""
import os
from datetime import date, timedelta
from types import SimpleNamespace

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.http import Http404
from django.utils import timezone

from .models import Assignment, GroupMember, Proposal, StudyGroup, Submission

MAX_CHAPTERS = 12


class ServiceError(Exception):
    """A rule was broken. str(error) is safe to show to the user."""


# ---------------------------------------------------------------- lookups / permissions

def _membership(group, user):
    if not getattr(user, 'is_authenticated', False):
        return None
    return GroupMember.objects.filter(group=group, user=user, status='active').first()


def is_active_member(user, group):
    return _membership(group, user) is not None


def is_evaluator(user, group):
    m = _membership(group, user)
    return m is not None and m.role == 'evaluator'


def is_student_member(user, group):
    m = _membership(group, user)
    return m is not None and m.role == 'member'


def get_group_or_404(user, pk):
    """Group only if the user is an ACTIVE member. 404 (not 403) so outsiders can't tell it exists."""
    group = StudyGroup.objects.filter(pk=pk).first()
    if group is None or not is_active_member(user, group):
        raise Http404
    return group


def get_proposal_or_404(user, pk):
    proposal = Proposal.objects.select_related('group').filter(pk=pk).first()
    if proposal is None or proposal.group is None or not is_active_member(user, proposal.group):
        raise Http404
    return proposal


def get_submission_or_404(user, pk):
    sub = Submission.objects.select_related('assignment__proposal__group').filter(pk=pk).first()
    if sub is None:
        raise Http404
    group = sub.assignment.proposal.group
    if group is None or not is_active_member(user, group):
        raise Http404
    return sub


def user_is_evaluator_anywhere(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    return GroupMember.objects.filter(user=user, role='evaluator', status='active').exists()


def my_groups(user):
    return StudyGroup.objects.filter(memberships__user=user, memberships__status='active').distinct()


def pending_invites(user):
    return GroupMember.objects.filter(user=user, status='invited').select_related('group', 'invited_by')


def progress_percent(proposal):
    total = proposal.assignments.count()
    if total == 0:
        return 0
    approved = sum(1 for a in proposal.assignments.all() if a.state == 'approved')
    return round(100 * approved / total)


def _require_evaluator(group, user):
    if not is_evaluator(user, group):
        raise ServiceError("Only the evaluator of this group can do that.")


def _require_student(group, user):
    if not is_student_member(user, group):
        raise ServiceError("Only group members (not the evaluator) can do that.")


# ---------------------------------------------------------------- file validation

def validate_upload(uploaded_file):
    if uploaded_file is None:
        raise ServiceError("Please choose a file.")
    allowed = [e.lower() for e in getattr(settings, 'ALLOWED_UPLOAD_EXTENSIONS', ['.pdf', '.doc', '.docx'])]
    max_mb = getattr(settings, 'MAX_UPLOAD_MB', 20)
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in allowed:
        raise ServiceError("File type not allowed. Use: " + ", ".join(allowed) + ".")
    if uploaded_file.size == 0:
        raise ServiceError("That file is empty.")
    if uploaded_file.size > max_mb * 1024 * 1024:
        raise ServiceError(f"File is too big (max {max_mb} MB).")


# ---------------------------------------------------------------- groups and invites

def create_group(user, name, image=None, invite_emails=()):
    """Creates the group; the creator becomes its evaluator. Returns (group, problems)."""
    name = (name or '').strip()
    if not name:
        raise ServiceError("Group name is required.")
    problems = []
    with transaction.atomic():
        group = StudyGroup.objects.create(name=name, created_by=user)
        if image:
            group.image = image
            group.save()
        GroupMember.objects.create(group=group, user=user, role='evaluator',
                                   status='active', joined_at=timezone.now())
        for email in invite_emails:
            email = (email or '').strip()
            if not email:
                continue
            try:
                invite(group, user, email)
            except ServiceError as e:
                problems.append(f"{email}: {e}")
    return group, problems


def invite(group, evaluator_user, email):
    _require_evaluator(group, evaluator_user)
    email = (email or '').strip()
    if not email:
        raise ServiceError("Enter an email.")
    target = User.objects.filter(email__iexact=email).first()
    if target is None:
        raise ServiceError("No account uses that email yet. They need to sign up first.")
    if target.pk == evaluator_user.pk:
        raise ServiceError("You can't invite yourself.")
    existing = GroupMember.objects.filter(group=group, user=target).first()
    if existing:
        if existing.status == 'active':
            raise ServiceError("They are already in this group.")
        if existing.status == 'invited':
            raise ServiceError("They already have a pending invite.")
        existing.status = 'invited'          # was declined -> invite again
        existing.invited_by = evaluator_user
        existing.save()
        return existing
    return GroupMember.objects.create(group=group, user=target, role='member',
                                      status='invited', invited_by=evaluator_user)


def respond_invite(membership, user, accept):
    if membership.user_id != user.pk or membership.status != 'invited':
        raise ServiceError("This invite isn't available.")
    if accept:
        membership.status = 'active'
        membership.joined_at = timezone.now()
    else:
        membership.status = 'declined'
    membership.save()
    return membership


def remove_member(group, evaluator_user, membership):
    _require_evaluator(group, evaluator_user)
    if membership.group_id != group.pk:
        raise ServiceError("That person isn't in this group.")
    if membership.user_id == evaluator_user.pk:
        raise ServiceError("The evaluator can't be removed.")
    membership.delete()


def leave_group(group, user):
    m = _membership(group, user)
    if m is None:
        raise ServiceError("You are not in this group.")
    if m.role == 'evaluator':
        raise ServiceError("The evaluator can't leave the group.")
    m.delete()


# ---------------------------------------------------------------- research + upload

def _add_version(assignment, user, uploaded_file):
    latest = assignment.latest
    return Submission.objects.create(
        assignment=assignment,
        version=(latest.version + 1) if latest else 1,
        file=uploaded_file,
        original_name=os.path.basename(uploaded_file.name)[:255],
        uploaded_by=user,
        status='pending',
    )


def start_research(group, user, title, description, uploaded_file):
    _require_student(group, user)
    if Proposal.objects.filter(group=group).exists():
        raise ServiceError("This group already has a research project.")
    title = (title or '').strip()
    if not title:
        raise ServiceError("Research title is required.")
    validate_upload(uploaded_file)
    with transaction.atomic():
        proposal = Proposal.objects.create(
            title=title, description=(description or '').strip(),
            group=group, submitted_by=user)
        tab = Assignment.objects.create(proposal=proposal, kind='proposal',
                                        title='Proposal', position=0)
        _add_version(tab, user, uploaded_file)
    return proposal


def submit(assignment, user, uploaded_file):
    group = assignment.proposal.group
    _require_student(group, user)
    validate_upload(uploaded_file)
    with transaction.atomic():
        locked = Assignment.objects.select_for_update().get(pk=assignment.pk)
        if not locked.is_unlocked:
            raise ServiceError("This tab is still locked. The previous one must be approved first.")
        if not locked.can_upload:
            raise ServiceError("You can't upload here right now (waiting for review, or already approved).")
        return _add_version(locked, user, uploaded_file)


# ---------------------------------------------------------------- plan (deadline + chapters)

def plot_due_dates(start, deadline, n):
    total = (deadline - start).days
    return [start + timedelta(days=round(total * i / n)) for i in range(1, n + 1)]  # last == deadline


def confirm_plan(proposal, evaluator_user, deadline, chapter_count, titles=None):
    group = proposal.group
    _require_evaluator(group, evaluator_user)
    if proposal.plan_confirmed_at:
        raise ServiceError("The plan is already set. Edit the tabs instead.")
    first = Assignment.objects.filter(proposal=proposal, position=0).first()
    if first is None or first.latest is None:
        raise ServiceError("Set up the plan after the proposal has been uploaded.")
    try:
        chapter_count = int(chapter_count)
    except (TypeError, ValueError):
        raise ServiceError("Chapter count must be a number.")
    if not 1 <= chapter_count <= MAX_CHAPTERS:
        raise ServiceError(f"Chapter count must be between 1 and {MAX_CHAPTERS}.")
    if not isinstance(deadline, date):
        raise ServiceError("Enter a valid deadline.")
    today = timezone.localdate()
    if deadline <= today + timedelta(days=chapter_count):
        raise ServiceError("The deadline is too close for that many chapters.")
    titles = list(titles or [])
    dates = plot_due_dates(today, deadline, chapter_count)
    with transaction.atomic():
        for i, due in enumerate(dates, start=1):
            title = (titles[i - 1].strip() if i - 1 < len(titles) and titles[i - 1] else '') or f"Chapter {i}"
            Assignment.objects.create(proposal=proposal, kind='chapter',
                                      title=title[:120], position=i, due_date=due)
        proposal.deadline = deadline
        proposal.plan_confirmed_at = timezone.now()
        proposal.save()


# ---------------------------------------------------------------- tab edits (evaluator only)

def rename_assignment(assignment, evaluator_user, title):
    _require_evaluator(assignment.proposal.group, evaluator_user)
    title = (title or '').strip()
    if not title:
        raise ServiceError("Tab name can't be empty.")
    assignment.title = title[:120]
    assignment.save()


def set_due_date(assignment, evaluator_user, due):
    _require_evaluator(assignment.proposal.group, evaluator_user)
    if due is not None and not isinstance(due, date):
        raise ServiceError("Enter a valid date.")
    assignment.due_date = due
    assignment.save()


def add_chapter(proposal, evaluator_user, title=None):
    _require_evaluator(proposal.group, evaluator_user)
    if not proposal.plan_confirmed_at:
        raise ServiceError("Set up the plan first.")
    chapters = proposal.assignments.filter(kind='chapter')
    if chapters.count() >= MAX_CHAPTERS:
        raise ServiceError(f"Max {MAX_CHAPTERS} chapters.")
    last = proposal.assignments.order_by('-position').first()
    position = last.position + 1
    return Assignment.objects.create(
        proposal=proposal, kind='chapter',
        title=((title or '').strip() or f"Chapter {position}")[:120],
        position=position, due_date=proposal.deadline)


def delete_last_chapter(assignment, evaluator_user):
    _require_evaluator(assignment.proposal.group, evaluator_user)
    if assignment.kind != 'chapter' or assignment.position == 0:
        raise ServiceError("The proposal tab can't be deleted.")
    last = assignment.proposal.assignments.order_by('-position').first()
    if last.pk != assignment.pk:
        raise ServiceError("Only the last chapter can be deleted.")
    if assignment.submissions.exists():
        raise ServiceError("This chapter already has uploads, so it can't be deleted.")
    assignment.delete()


# ---------------------------------------------------------------- review

def review(submission, evaluator_user, decision, feedback=''):
    feedback = (feedback or '').strip()
    if decision not in ('approve', 'reject'):
        raise ServiceError("Unknown decision.")
    with transaction.atomic():
        # of=('self',): lock only the submission row (Postgres can't lock a nullable join side)
        sub = (Submission.objects.select_for_update(of=('self',))
               .select_related('assignment__proposal__group').get(pk=submission.pk))
        _require_evaluator(sub.assignment.proposal.group, evaluator_user)
        latest = sub.assignment.latest
        if latest is None or latest.pk != sub.pk:
            raise ServiceError("Only the newest upload can be reviewed.")
        if sub.status != 'pending':
            raise ServiceError("This upload was already reviewed.")
        if decision == 'reject' and not feedback:
            raise ServiceError("Please write feedback when rejecting.")
        sub.status = 'approved' if decision == 'approve' else 'rejected'
        sub.feedback = feedback
        sub.reviewed_by = evaluator_user
        sub.reviewed_at = timezone.now()
        sub.save()
        return sub


# ---------------------------------------------------------------- read helpers for dashboard / calendar / profile

def research_cards(user):
    """One entry per research project in my groups, newest first."""
    groups = my_groups(user)
    roles = dict(GroupMember.objects.filter(user=user, status='active').values_list('group_id', 'role'))
    proposals = (Proposal.objects.filter(group__in=groups)
                 .select_related('group').prefetch_related('assignments__submissions')
                 .order_by('-created_at'))
    cards = []
    for p in proposals:
        percent = progress_percent(p)
        cards.append(SimpleNamespace(
            proposal=p, pk=p.pk, title=p.title, created_at=p.created_at, group=p.group,
            percent=percent, progress_label=f"{percent}% approved",
            role=roles.get(p.group_id, 'member'),
            pill='approved' if percent == 100 else 'pending'))
    return cards


def dashboard_stats(user):
    """Numbers for the dashboard + the evaluator's review queue."""
    cards = research_cards(user)
    waiting = approved = returned = 0
    queue = []
    for c in cards:
        for a in c.proposal.assignments.all():
            state = a.state
            if state == 'pending':
                waiting += 1
                if c.role == 'evaluator':
                    queue.append(SimpleNamespace(
                        title=a.title, research=c.title, position=a.position,
                        research_pk=c.pk, submitted_at=a.latest.submitted_at))
            elif state == 'approved':
                approved += 1
            elif state == 'rejected':
                returned += 1
    queue.sort(key=lambda q: q.submitted_at)
    return {
        'cards': cards,
        'total': len(cards),
        'waiting': waiting,
        'approved': approved,
        'returned': returned,
        'review_queue': queue,
        'needs_group': not my_groups(user).exists() and not pending_invites(user).exists(),
    }


def _due_item(a, today):
    state = a.state
    if state == 'approved':
        css, label = 'done', 'Approved'
    elif state == 'pending':
        css, label = 'in_progress', 'Waiting for review'
    elif a.due_date and a.due_date < today:
        css, label = 'overdue', 'Overdue'
    elif state == 'rejected':
        css, label = 'pending', 'Returned'
    else:
        css, label = 'pending', 'To do'
    return SimpleNamespace(title=a.title, research=a.proposal.title, due_date=a.due_date,
                           status=css, label=label, done=(state == 'approved'),
                           research_pk=a.proposal_id, position=a.position)


def _my_assignments(user):
    return (Assignment.objects.filter(proposal__group__in=my_groups(user), due_date__isnull=False)
            .select_related('proposal').prefetch_related('submissions'))


def calendar_items(user, start, end, today):
    return [_due_item(a, today) for a in
            _my_assignments(user).filter(due_date__range=(start, end)).order_by('due_date')]


def upcoming_items(user, today, limit=6):
    items = [_due_item(a, today) for a in _my_assignments(user).order_by('due_date')]
    return [i for i in items if not i.done][:limit]