from django.shortcuts import render


def terms(request):
    """Static Terms and Conditions page (sample text for the capstone demo)."""
    return render(request, 'core/terms.html')
