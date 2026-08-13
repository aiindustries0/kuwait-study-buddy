import json
import os
import sqlite3
import time
from datetime import date

import requests
from dotenv import load_dotenv
from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for

from auth import authenticate_user, create_user, get_user_by_id, init_db, login_required

load_dotenv()
AI_NOT_CONFIGURED = "AI not configured yet"
SUBJECT_TOPICS = {
    "Math": ["Algebra", "Functions", "Polynomials", "Coordinate Geometry", "Trigonometry", "Statistics & Probability"],
    "Physics": ["Measurement", "Vectors", "Motion", "Newton's Laws", "Work Energy Power"],
    "Chemistry": ["Atomic Structure", "Periodic Table", "Chemical Bonding", "Stoichiometry", "Chemical Reactions"],
    "Biology": ["Cells", "Biochemistry", "Microorganisms", "Genetics", "Ecology"],
    "English": ["Reading & Comprehension", "Grammar & Writing", "Vocabulary"],
    "Arabic": ["Grammar & Writing", "Reading & Comprehension", "Literature"],
    "Islamic Studies": ["Aqeedah & Fiqh", "Seerah", "Hadith & Ethics"],
    "Computer Skills": ["Digital Literacy", "Productivity Tools", "Online Safety"],
}
DIFFICULTIES = ["Easy", "Medium", "Hard"]


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    secret = os.environ.get("FLASK_SECRET_KEY")
    if not secret:
        if os.environ.get("FLASK_ENV", "development").lower() == "production":
            raise RuntimeError("FLASK_SECRET_KEY must be set in production")
        secret = "dev-only-secret-key-not-for-production"
    app.config.from_mapping(SECRET_KEY=secret, DATABASE=os.environ.get("DATABASE_PATH", os.path.join(app.instance_path, "study_buddy.sqlite3")))
    os.makedirs(app.instance_path, exist_ok=True)
    init_db(app.config["DATABASE"])
    init_learning_db(app.config["DATABASE"])

    @app.before_request
    def load_user():
        uid = session.get("user_id")
        g.user = get_user_by_id(app.config["DATABASE"], uid) if uid else None

    @app.get("/")
    def index(): return render_template("index.html")

    @app.route("/signup", methods=("GET", "POST"))
    def signup():
        if g.user is not None: return redirect(url_for("dashboard"))
        name = email = ""
        if request.method == "POST":
            name, email = request.form.get("name", "").strip(), request.form.get("email", "").strip().lower()
            password, confirmation = request.form.get("password", ""), request.form.get("confirm_password", "")
            if not name: flash("Please enter your name.", "error")
            elif len(name) > 80: flash("Your name must be 80 characters or fewer.", "error")
            elif not email or "@" not in email or "." not in email.rsplit("@", 1)[-1]: flash("Please enter a valid email address.", "error")
            elif len(email) > 254: flash("That email address is too long.", "error")
            elif len(password) < 8: flash("Your password must be at least 8 characters.", "error")
            elif password != confirmation: flash("The passwords do not match.", "error")
            elif not create_user(app.config["DATABASE"], name, email, password): flash("An account with that email already exists. Try logging in.", "error")
            else:
                flash("Account created. You can now log in.", "success")
                return redirect(url_for("login"))
        return render_template("signup.html", name=name, email=email)

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if g.user is not None: return redirect(url_for("dashboard"))
        email = ""
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = authenticate_user(app.config["DATABASE"], email, request.form.get("password", ""))
            if user is None: flash("Check your email and password, then try again.", "error")
            else:
                session.clear(); session["user_id"] = user["id"]; flash("You are signed in.", "success")
                return redirect(url_for("dashboard"))
        return render_template("login.html", email=email)

    @app.get("/logout")
    def logout():
        session.clear(); flash("You have been signed out.", "success"); return redirect(url_for("index"))

    @app.get("/dashboard")
    @login_required
    def dashboard():
        recent, weak = progress_for_user(app.config["DATABASE"], g.user["id"])
        return render_template("dashboard.html", user=g.user, recent_scores=recent, needs_review=weak)

    @app.route("/quiz", methods=("GET", "POST"))
    @login_required
    def quiz():
        if request.method == "POST":
            subject, topic, difficulty = (request.form.get(k, "").strip() for k in ("subject", "topic", "difficulty"))
            if subject not in SUBJECT_TOPICS or topic not in SUBJECT_TOPICS[subject]: flash("Choose a subject and topic from the study list.", "error")
            elif difficulty not in DIFFICULTIES: flash("Choose a quiz difficulty.", "error")
            else:
                questions, error = generate_quiz(subject, topic, difficulty)
                if error:
                    return render_template("quiz.html", active_quiz=None, subjects=list(SUBJECT_TOPICS), topics_by_subject=SUBJECT_TOPICS, difficulties=DIFFICULTIES, ai_error=error)
                session["quiz"] = {"subject": subject, "topic": topic, "difficulty": difficulty, "questions": questions}
                return redirect(url_for("quiz"))
        return render_template("quiz.html", active_quiz=session.get("quiz"), subjects=list(SUBJECT_TOPICS), topics_by_subject=SUBJECT_TOPICS, difficulties=DIFFICULTIES, ai_error=None)

    @app.post("/quiz/check")
    @login_required
    def check_answer():
        data, quiz_data = request.get_json(silent=True) or {}, session.get("quiz")
        try: index = int(data.get("question_index"))
        except (TypeError, ValueError): return jsonify(error="That answer could not be checked."), 400
        if not quiz_data or not 0 <= index < len(quiz_data["questions"]): return jsonify(error="This quiz is no longer active."), 400
        answer = str(data.get("answer", "")).strip(); question = quiz_data["questions"][index]
        if not answer: return jsonify(error="Choose an answer first."), 400
        return jsonify(question_index=index, correct=answer.casefold() == question["answer"].casefold(), correct_answer=question["answer"], explanation=question["explanation"])

    @app.post("/quiz/submit")
    @login_required
    def submit_quiz():
        quiz_data, data = session.get("quiz"), request.get_json(silent=True) or {}
        answers = data.get("answers") or {}
        if not quiz_data or not isinstance(answers, dict): return jsonify(error="This quiz is no longer active."), 400
        questions = quiz_data["questions"]
        score = sum(str(answers.get(str(i), "")).strip().casefold() == q["answer"].casefold() for i, q in enumerate(questions))
        total, result_date = len(questions), date.today().isoformat()
        db = learning_db(app.config["DATABASE"])
        db.execute("INSERT INTO quiz_results (user_id, subject, topic, score, total, date) VALUES (?, ?, ?, ?, ?, ?)", (g.user["id"], quiz_data["subject"], quiz_data["topic"], score, total, result_date)); db.commit(); db.close()
        session.pop("quiz", None)
        return jsonify(score=score, total=total, percentage=round(score / total * 100) if total else 0, status=status_for(score, total), dashboard_url=url_for("dashboard"))

    @app.route("/explain", methods=("GET", "POST"))
    @login_required
    def explain():
        topic = request.form.get("topic", "").strip() if request.method == "POST" else ""
        question = request.form.get("question", "").strip() if request.method == "POST" else ""
        mode = request.form.get("mode", "simplify") if request.method == "POST" else "simplify"
        answer = error = None
        if request.method == "POST":
            if not topic or not question: flash("Add a topic and question so the AI can help.", "error")
            elif mode not in {"simplify", "example"}: flash("Choose how you want the idea explained.", "error")
            else: answer, error = generate_explanation(topic, question, mode)
        return render_template("explain.html", topic=topic, question=question, mode=mode, explanation=answer, ai_error=error)

    return app


def learning_db(path):
    db = sqlite3.connect(path); db.row_factory = sqlite3.Row; return db


def init_learning_db(path):
    db = learning_db(path)
    db.execute("CREATE TABLE IF NOT EXISTS quiz_results (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, subject TEXT NOT NULL, topic TEXT NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL, date TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id))")
    db.commit(); db.close()


def status_for(score, total):
    percent = score / total * 100 if total else 0
    return "strong" if percent >= 80 else "developing" if percent >= 60 else "needs-review"


def progress_for_user(path, user_id):
    db = learning_db(path)
    recent = db.execute("SELECT subject, topic, score, total, date FROM quiz_results WHERE user_id=? ORDER BY id DESC LIMIT 6", (user_id,)).fetchall()
    grouped = db.execute("SELECT subject, topic, SUM(score) score, SUM(total) total FROM quiz_results WHERE user_id=? GROUP BY subject, topic ORDER BY topic", (user_id,)).fetchall(); db.close()
    def decorate(row):
        item = dict(row); item["percentage"] = round(item["score"] / item["total"] * 100) if item["total"] else 0; item["status"] = status_for(item["score"], item["total"]); return item
    recent = [decorate(row) for row in recent]; grouped = [decorate(row) for row in grouped]
    return recent, [row for row in grouped if row["status"] == "needs-review"]


def gemini_call(prompt, json_mode=False):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key: return None, AI_NOT_CONFIGURED
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.35}}
    if json_mode: payload["generationConfig"]["responseMimeType"] = "application/json"

    def api_error_message(response):
        try:
            details = response.json()
        except (ValueError, TypeError):
            details = None
        if isinstance(details, dict):
            error = details.get("error", details)
            if isinstance(error, dict):
                message = error.get("message") or error.get("status")
            else:
                message = str(error) if error else None
            if message: return str(message)
        return (getattr(response, "text", "") or getattr(response, "reason", "") or "Unknown API error").strip()

    for attempt in range(4):
        try:
            response = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent", params={"key": key}, json=payload, timeout=45)
            if response.status_code == 429:
                if attempt < 3:
                    time.sleep((15, 30, 60)[attempt])
                    continue
                return None, "AI is rate limited — wait a minute and try again"
            if 500 <= response.status_code <= 599:
                if attempt < 2:
                    time.sleep(2)
                    continue
                return None, f"AI request failed (HTTP {response.status_code}): {api_error_message(response)}"
            if not response.ok:
                return None, f"AI request failed (HTTP {response.status_code}): {api_error_message(response)}"
            data = response.json()
            text = "".join(part.get("text", "") for part in data.get("candidates", [])[0].get("content", {}).get("parts", [])).strip()
            return (text, None) if text else (None, "The AI did not return an answer. Please try again.")
        except requests.RequestException as exc:
            return None, f"AI request failed: {exc or 'network error'}"
        except (ValueError, IndexError, AttributeError, KeyError) as exc:
            return None, f"AI response parsing failed: {exc}"


def extract_json(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith("```"): lines = lines[1:]
        if lines and lines[-1].strip() == "```": lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try: return json.loads(cleaned)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for i, char in enumerate(cleaned):
            if char in "[{":
                try: return decoder.raw_decode(cleaned[i:])[0]
                except json.JSONDecodeError: pass
    return None


def normalize_question(raw):
    if not isinstance(raw, dict): return None
    text, explanation = str(raw.get("question") or raw.get("prompt") or "").strip(), str(raw.get("explanation") or raw.get("why") or "").strip()
    kind = str(raw.get("type") or raw.get("question_type") or "").lower().replace(" ", "_").replace("-", "_")
    if kind in {"true_false", "truefalse", "tf", "boolean", "true/false"}: kind, choices = "true_false", ["True", "False"]
    elif kind in {"mcq", "multiple_choice"}:
        choices = raw.get("choices", raw.get("options"));
        if not isinstance(choices, list) or len(choices) != 4: return None
        choices = [str(x).strip() for x in choices]
        if any(not x for x in choices) or len(set(choices)) != 4: return None
    else: return None
    if not text or not explanation: return None
    answer = raw.get("answer", raw.get("correct_answer"))
    if kind == "true_false":
        answer = "True" if answer is True or str(answer).strip().lower() in {"true", "t"} else "False" if answer is False or str(answer).strip().lower() in {"false", "f"} else ""
    elif isinstance(answer, int) and 0 <= answer < 4: answer = choices[answer]
    else: answer = str(answer or "").strip()
    return {"type": kind, "question": text, "choices": choices, "answer": answer, "explanation": explanation} if answer in choices else None


def generate_quiz(subject, topic, difficulty):
    prompt = f'''Create a careful quiz for a Kuwaiti 10th-grade student. Subject: {subject}. Topic: {topic}. Difficulty: {difficulty}.
Return ONLY valid JSON, an array of exactly 5 objects: exactly 3 type "multiple_choice" and exactly 2 type "true_false". Each multiple_choice has exactly 4 distinct choices. Each true_false has choices ["True", "False"]. Every object has only: type, question, choices, answer, explanation. The answer must exactly match one choice. Keep it accurate, age-appropriate, unambiguous, and do not repeat concepts.'''
    text, error = gemini_call(prompt, True)
    if error: return None, error
    parsed = extract_json(text); raw = parsed.get("questions") if isinstance(parsed, dict) else parsed
    if not isinstance(raw, list) or len(raw) != 5: return None, "The AI returned an invalid quiz. Please try again."
    questions = [normalize_question(item) for item in raw]
    if any(q is None for q in questions) or sum(q["type"] == "multiple_choice" for q in questions) != 3 or sum(q["type"] == "true_false" for q in questions) != 2: return None, "The AI returned an invalid quiz. Please try again."
    return questions, None


def generate_explanation(topic, question, mode):
    direction = "Explain it simply in short steps." if mode == "simplify" else "Explain it with one everyday example and connect that example back to the idea."
    return gemini_call(f'''You are a patient tutor for a Kuwaiti 10th-grade student. Topic: {topic}. Question: {question}. {direction} Use clear English, a friendly tone, no university terminology, and no more than five short paragraphs. Do not mention that you are an AI.''')


app = create_app()
if __name__ == "__main__": app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")
