from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.db import models


def private_storage():
    # Research files live OUTSIDE media/ and are only served by a permission-checked view.
    # A callable, so migrations don't hard-code a path.
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


class Proposal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revision', 'Needs Revision'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField()
    file = models.FileField(upload_to='proposals/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proposals')
    created_at = models.DateTimeField(auto_now_add=True)

    # --- Groups rebuild: a Proposal is now the research of ONE group ---
    # file / status above are DEPRECATED (kept for old rows). submitted_by = first uploader.
    group = models.OneToOneField('StudyGroup', on_delete=models.CASCADE,
                                 null=True, blank=True, related_name='research')
    deadline = models.DateField(null=True, blank=True)              # final deadline
    plan_confirmed_at = models.DateTimeField(null=True, blank=True)  # set when the evaluator confirms the plan

    def __str__(self):
        return self.title


class ProposalRevision(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='revisions')
    revised_file = models.FileField(upload_to='proposal_revisions/')
    revision_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Revision for {self.proposal.title}"


class Evaluation(models.Model):
    DECISION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('revise', 'Request Revision'),
    ]
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='evaluations')
    evaluator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evaluations')
    comments = models.TextField(blank=True)
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evaluation of {self.proposal.title} by {self.evaluator.username}"


class Project(models.Model):
    STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed'),
    ]
    proposal = models.OneToOneField(Proposal, on_delete=models.CASCADE, related_name='project')
    title = models.CharField(max_length=255)
    start_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ongoing')

    def __str__(self):
        return self.title


class Milestone(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=255)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return self.title


class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ]
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name='tasks')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    description = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return self.description


class ProgressReport(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='progress_reports')
    week = models.PositiveIntegerField()
    accomplishment = models.TextField()
    percentage = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Week {self.week} - {self.project.title}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message


class ChapterSubmission(models.Model):
    # DEPRECATED: replaced by Assignment/Submission. Kept for old rows.
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('revision', 'Needs Revision'),
        ('rejected', 'Rejected'),
    ]
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='chapters')
    chapter = models.PositiveSmallIntegerField()
    file = models.FileField(upload_to='chapters/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['chapter']
        unique_together = ('proposal', 'chapter')

    def __str__(self):
        return f"Chapter {self.chapter} - {self.proposal.title}"


class Profile(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    program = models.CharField(max_length=150, blank=True)
    bio = models.TextField(max_length=300, blank=True)
    avatar = models.FileField(upload_to='avatars/', blank=True)
    banner = models.FileField(upload_to='banners/', blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class StudyGroup(models.Model):
    name = models.CharField(max_length=120)
    image = models.FileField(upload_to='groups/', blank=True)
    # DEPRECATED: replaced by GroupMember (below). Kept until the data copy is verified.
    members = models.ManyToManyField(User, related_name='study_groups', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_groups')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class GroupMember(models.Model):
    ROLE_CHOICES = [('evaluator', 'Evaluator'), ('member', 'Member')]
    STATUS_CHOICES = [('invited', 'Invited'), ('active', 'Active'), ('declined', 'Declined')]

    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='invited')
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    joined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('group', 'user')
        constraints = [
            models.UniqueConstraint(
                fields=['group'], condition=models.Q(role='evaluator'),
                name='one_evaluator_per_group'),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.group.name} ({self.role}, {self.status})"


class Assignment(models.Model):
    """One tab of a group's research: position 0 = proposal, 1..N = chapters."""
    KIND_CHOICES = [('proposal', 'Proposal'), ('chapter', 'Chapter')]

    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='assignments')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='chapter')
    title = models.CharField(max_length=120)  # renamable tab label
    position = models.PositiveSmallIntegerField()
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position']
        unique_together = ('proposal', 'position')

    def __str__(self):
        return f"{self.title} ({self.proposal_id})"

    @property
    def latest(self):
        """Newest Submission or None (Submission is ordered by -version)."""
        return self.submissions.first()

    @property
    def state(self):
        """'empty' | 'pending' | 'approved' | 'rejected'"""
        latest = self.latest
        return latest.status if latest else 'empty'

    @property
    def is_unlocked(self):
        if self.position == 0:
            return True
        prev = Assignment.objects.filter(proposal_id=self.proposal_id, position=self.position - 1).first()
        return prev is not None and prev.state == 'approved'

    @property
    def can_upload(self):
        return self.is_unlocked and self.state in ('empty', 'rejected')


class Submission(models.Model):
    """One uploaded version of an Assignment. Every upload is kept (history)."""
    STATUS_CHOICES = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    version = models.PositiveIntegerField()
    file = models.FileField(upload_to='submissions/', storage=private_storage)
    original_name = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='submissions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    feedback = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']
        unique_together = ('assignment', 'version')

    def __str__(self):
        return f"{self.assignment.title} v{self.version} ({self.status})"