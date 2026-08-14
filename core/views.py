from django.http import HttpResponse


def test_backend(request):
    return HttpResponse("ReHub Django backend is working!")