# Kuwaiti 10th Grade AI Study Buddy

A beginner-friendly Flask study companion for **Mohammad Aldaoseri**, designed for a focused, portrait-first study experience for Kuwaiti 10th grade students. This scaffold includes a polished landing page, local signup/login, a protected dashboard, and a lightweight SQLite user store.

> **Status:** Gemini integration is planned for a later phase. This version intentionally includes no Gemini integration, deployment configuration, or test credentials.

## Prerequisites

- Python 3.10 or newer
- `pip`
- A modern web browser

## Install

```bash
git clone https://github.com/aiindustries0/kuwait-study-buddy.git
cd kuwait-study-buddy
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On Windows PowerShell, create/activate the environment with `py -m venv .venv` and `.venv\\Scripts\\Activate.ps1`.

## Configuration

The app uses `FLASK_SECRET_KEY` to sign Flask sessions. For local development only, it falls back to `dev-only-change-me` when the variable is absent. Set a long, random, unique value before sharing or deploying:

```bash
export FLASK_SECRET_KEY="replace-this-with-a-long-random-development-value"
```

PowerShell: `$env:FLASK_SECRET_KEY = "replace-this-with-a-long-random-development-value"`. The app loads a local `.env` file when present, and `.env` is ignored by Git. `DATABASE_PATH` can optionally point to a different SQLite file.

## Run

With the virtual environment active:

```bash
python app.py
```

Open <http://127.0.0.1:5000>. For the development reloader, use `FLASK_DEBUG=1 python app.py` (PowerShell: `$env:FLASK_DEBUG = "1"; python app.py`).

## Database behavior

On startup the app automatically creates `instance/` and initializes `instance/study_buddy.sqlite3`. It creates a `users` table with a unique, normalized email and stores passwords only as Werkzeug hashes. The local SQLite database is ignored by Git and no users or test credentials are bundled.

## Project layout

```text
app.py
auth.py
requirements.txt
static/style.css
templates/base.html
templates/index.html
templates/login.html
templates/signup.html
templates/dashboard.html
.gitignore
```

## Next phase

Gemini-powered study assistance is planned later. The current UI and authentication foundation are intentionally independent so future AI features can be added without storing API keys in source control.
