from django.db import models
from django.contrib.auth.models import User


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