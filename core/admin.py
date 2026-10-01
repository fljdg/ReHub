from django.contrib import admin
from .models import (
    Proposal, ProposalRevision, Evaluation,
    Project, Milestone, Task, ProgressReport, Notification,
    ChapterSubmission, Profile, StudyGroup
)

admin.site.register(Proposal)
admin.site.register(ProposalRevision)
admin.site.register(Evaluation)
admin.site.register(Project)
admin.site.register(Milestone)
admin.site.register(Task)
admin.site.register(ProgressReport)
admin.site.register(Notification)
admin.site.register(ChapterSubmission)
admin.site.register(Profile)
admin.site.register(StudyGroup)
