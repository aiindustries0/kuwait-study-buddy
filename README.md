# Kuwaiti 10th Grade AI Study Buddy

A beginner-friendly Flask study companion for Kuwaiti 10th-grade students. It preserves the original sign-up/login foundation and dark, touch-friendly iPad UI while adding AI-powered practice and explanations.

## Features

- Protected `/quiz` setup for subject, topic, and difficulty.
- Gemini generates exactly five strict-JSON questions: three multiple-choice and two true/false. Responses are defensively parsed and validated before display.
- One-question-per-screen touch flow with immediate correctness and explanation feedback. Final scoring is always performed in Python.
- SQLite persistence for each user's score, total, topic, subject, and date.
- Weak-area status: **strong** at 80% or higher, **developing** from 60–79%, and **needs-review** below 60%.
- Dashboard recent scores and aggregated needs-review topics.
- Protected `/explain` tool with **Simplify it** and **Give an example** options, tuned for 10th-grade explanations.
- Subjects and topics include Math (Algebra, Functions, Polynomials, Coordinate Geometry, Trigonometry, Statistics & Probability), Physics (Measurement, Vectors, Motion, Newton's Laws, Work Energy Power), Chemistry (Atomic Structure, Periodic Table, Chemical Bonding, Stoichiometry, Chemical Reactions), Biology (Cells, Biochemistry, Microorganisms, Genetics, Ecology), English, Arabic, Islamic Studies, and Computer Skills.

## Run locally

```bash
git clone https://github.com/aiindustries0/kuwait-study-buddy.git
cd kuwait-study-buddy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_SECRET_KEY="use-a-long-random-value"
export GEMINI_API_KEY="your-gemini-api-key"
python app.py
```

Open <http://127.0.0.1:5000>. Without a Gemini key, the quiz and explanation forms show the exact message `AI not configured yet`; no secret is stored in the repository.

## Render deployment

Use the existing `Procfile` (`web: gunicorn app:app`) and add this Render environment variable:

- `GEMINI_API_KEY` — your Google Gemini API key

Also set a strong `FLASK_SECRET_KEY`. `DATABASE_PATH` may point to a persistent SQLite disk; otherwise quiz results use the instance filesystem.

## Project layout

```text
app.py
auth.py
requirements.txt
static/style.css
templates/
  base.html
  dashboard.html
  explain.html
  index.html
  login.html
  quiz.html
  signup.html
```
