"""Search logic for the top search bar.

Every word typed must appear in the title (or description), so "climate survey" only
matches things that mention both words. Everyone, staff included, searches only the
research of the groups they are an active member of.
"""
from django.db.models import Q

from . import services
from .models import Assignment, Proposal

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

    proposals = Proposal.objects.filter(group__in=services.my_groups(user))

    found_proposals = list(
        proposals.filter(_terms_filter(terms, ['title', 'description']))
        .select_related('group').order_by('-created_at')[:MAX_RESULTS]
    )
    for p in found_proposals:
        p.percent = services.progress_percent(p)

    found_tabs = list(
        Assignment.objects.filter(proposal__in=proposals)
        .filter(_terms_filter(terms, ['title']))
        .select_related('proposal').order_by('proposal_id', 'position')[:MAX_RESULTS]
    )

    return {
        'proposals': found_proposals,
        'tabs': found_tabs,
        'total': len(found_proposals) + len(found_tabs),
    }