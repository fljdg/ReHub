from django.contrib import admin
from .models import (
    Proposal, ProposalRevision, Evaluation,
    Project, Milestone, Task, ProgressReport, Notification,
    ChapterSubmission, Profile, StudyGroup,
    GroupMember, Assignment, Submission,
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


@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'role', 'status', 'joined_at')
    list_filter = ('role', 'status')


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('proposal', 'position', 'title', 'kind', 'due_date')
    list_filter = ('kind',)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'version', 'status', 'uploaded_by', 'submitted_at')
    list_filter = ('status',)