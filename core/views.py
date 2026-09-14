from django.http import HttpResponse
from django.shortcuts import render, redirect


def test_backend(request):
    return HttpResponse("ReHub Django backend is working!")


# ---------------------------------------------------------------
# PUBLIC / MARKETING PAGES
# Templates live in frontend/templates/public/pages/. Each view
# below is intentionally thin — the real markup is assembled
# block by block via {% include %} inside the templates.
# ---------------------------------------------------------------

def public_home(request):
    return render(request, "public/pages/home.html")


def public_login(request):
    form_error = None
    if request.method == "POST":
        # TODO: hook this up to your real authentication once the
        # user model / auth backend is in place.
        form_error = "Login isn't wired up to an account system yet."
    return render(request, "public/pages/login.html", {"form_error": form_error})


def public_get_started(request):
    form_error = None
    if request.method == "POST":
        # TODO: hook this up to your real sign-up flow once the
        # user model is in place.
        form_error = "Sign-up isn't wired up to an account system yet."
    return render(request, "public/pages/get_started.html", {"form_error": form_error})