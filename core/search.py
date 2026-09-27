"""Search logic for the top search bar.

Every word typed must appear in the title or description, so "climate survey" only
matches things that mention both words. Students search their own work; staff
(evaluators/admins) search everyone's.
"""
from django.db.models import Q

from .models import Milestone, Project, Proposal

MAX_RESULTS = 25


def _terms_filter(terms, fields):
    condition = Q()
    for term in terms:
        term_match = Q()
        for field in fields:
            term_match |= Q(**{f'{field}__icontains': term})
        condition &= term_match
    return condition


def run_search(user, query):
    terms = query.split()[:6]

    proposals = Proposal.objects.all() if user.is_staff else Proposal.objects.filter(submitted_by=user)
    visible_ids = proposals.values('id')

    found_proposals = list(
        proposals.filter(_terms_filter(terms, ['title', 'description']))
        .select_related('submitted_by').order_by('-created_at')[:MAX_RESULTS]
    )
    found_projects = list(
        Project.objects.filter(proposal_id__in=visible_ids)
        .filter(_terms_filter(terms, ['title'])).order_by('-start_date')[:MAX_RESULTS]
    )
    found_milestones = list(
        Milestone.objects.filter(project__proposal_id__in=visible_ids)
        .filter(_terms_filter(terms, ['title'])).select_related('project').order_by('due_date')[:MAX_RESULTS]
    )

    return {
        'proposals': found_proposals,
        'projects': found_projects,
        'milestones': found_milestones,
        'total': len(found_proposals) + len(found_projects) + len(found_milestones),
    }
