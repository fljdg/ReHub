# ReHub — merged project

This merges the two uploaded copies of the project:

- **ReHub.zip** — had the real backend: Postgres/Supabase connection via `.env`,
  the full domain model (`Proposal`, `ProposalRevision`, `Evaluation`, `Project`,
  `Milestone`, `Task`, `ProgressReport`, `Notification`) registered in `admin.py`,
  and Django/DB setup. Its UI (both the public marketing pages and the dashboard
  shell) was the **old** design — its own git log shows the last commit was
  literally "restore design tokens... lost in merge".
- **rehub.zip** — had the **new** UI: the redesigned landing page (hero, features
  carousel, demonstration, about, team, footer/feedback form) and dashboard shell
  (collapsible sidebar, topbar) matching the newer Canva/Figma design. But its
  `core/models.py` was empty — no domain models at all — and `signup_view` was a
  stub that rendered a form but never created an account.

## What this merged copy keeps from each

From **ReHub.zip** (backend):
- `config/settings.py` — Postgres via `.env`, `python-dotenv`
- `core/models.py`, `core/admin.py`, `core/migrations/0001_initial.py` — the full domain model

From **rehub.zip** (UI):
- `core/templates/core/*.html` — the new landing page, login, signup, dashboard shell
- `core/static/core/**` — the new stylesheet and images

## What was fixed/wired up while merging

- `signup_view` now actually creates a `django.contrib.auth.User` (it validates
  matching passwords, min length, and duplicate email, and auto-generates a
  username from the email). Previously it just rendered the template and did nothing.
- `login_view` / `logout_view` / `dashboard` now live alongside the new templates
  and use real `django.contrib.auth`.
- Templates + static were moved from the old `frontend/` app into `core/templates/core/`
  and `core/static/core/`, so Django's app-directories finder picks them up
  automatically — the old project-level `STATICFILES_DIRS`/`TEMPLATES.DIRS`
  pointing at `frontend/` were removed since that app no longer exists.
- `core/urls.py` now uses `app_name = 'core'` (matching what the new templates'
  `{% url %}` tags expect: `core:home`, `core:login`, `core:signup`, `core:dashboard`).
- Added `LOGIN_URL` / `LOGIN_REDIRECT_URL` / `LOGOUT_REDIRECT_URL` to settings.
- Added `MEDIA_URL` / `MEDIA_ROOT` (+ dev URL serving) since `Proposal.file` and
  `ProposalRevision.revised_file` are `FileField`s that need somewhere to upload to.
- Dashboard now shows the logged-in user's real proposal count and a small table
  of their most recent proposals (pulled from the DB) instead of static placeholder text.
- `TIME_ZONE` set to `Asia/Manila`.
- `requirements.txt` cleaned up (dropped the unused `mysqlclient`, since the DB is Postgres).
- `.env` was **not** copied into this zip — it had a live Supabase DB password in
  it. Use the included `.env.example` as a template and put your real values in
  your own `.env` (which is already gitignored). **You should rotate that Supabase
  password**, since it was sitting in the uploaded file in plaintext.

## Still on you / not yet wired up

- Proposal submission, evaluation, and milestone/task views+templates don't exist
  yet — the models and admin are there, but there's no user-facing UI for them
  beyond the dashboard's read-only proposal list. That's the natural next slice
  of work once you're happy with this merge.
- The public "Login"/"Get Started" pages that were on the *old* UI's separate
  `public/` template set are gone (superseded by the new UI's `login.html`/`signup.html`).
- No automated tests were added (`core/tests.py` is still the stub from ReHub.zip).

## Running it

```bash
cd ReHub
python -m venv venv
source venv/bin/activate   # venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env       # then fill in your real DB creds + a fresh secret key
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
