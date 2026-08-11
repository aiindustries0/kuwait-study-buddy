import os

from dotenv import load_dotenv
from flask import Flask, flash, g, redirect, render_template, request, session, url_for

from auth import authenticate_user, create_user, get_user_by_id, init_db, login_required

load_dotenv()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.environ.get("DATABASE_PATH", os.path.join(app.instance_path, "study_buddy.sqlite3")),
    )
    os.makedirs(app.instance_path, exist_ok=True)
    init_db(app.config["DATABASE"])

    @app.before_request
    def load_logged_in_user():
        user_id = session.get("user_id")
        g.user = get_user_by_id(app.config["DATABASE"], user_id) if user_id else None

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.route("/signup", methods=("GET", "POST"))
    def signup():
        if g.user is not None:
            return redirect(url_for("dashboard"))
        name = email = ""
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirmation = request.form.get("confirm_password", "")
            if not name:
                flash("Please enter your name.", "error")
            elif len(name) > 80:
                flash("Your name must be 80 characters or fewer.", "error")
            elif not email or "@" not in email or "." not in email.rsplit("@", 1)[-1]:
                flash("Please enter a valid email address.", "error")
            elif len(email) > 254:
                flash("That email address is too long.", "error")
            elif len(password) < 8:
                flash("Your password must be at least 8 characters.", "error")
            elif password != confirmation:
                flash("The passwords do not match.", "error")
            elif not create_user(app.config["DATABASE"], name, email, password):
                flash("An account with that email already exists. Try logging in.", "error")
            else:
                flash("Account created. You can now log in.", "success")
                return redirect(url_for("login"))
        return render_template("signup.html", name=name, email=email)

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if g.user is not None:
            return redirect(url_for("dashboard"))
        email = ""
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = authenticate_user(app.config["DATABASE"], email, request.form.get("password", ""))
            if user is None:
                flash("Check your email and password, then try again.", "error")
            else:
                session.clear()
                session["user_id"] = user["id"]
                flash("You are signed in.", "success")
                return redirect(url_for("dashboard"))
        return render_template("login.html", email=email)

    @app.get("/logout")
    def logout():
        session.clear()
        flash("You have been signed out.", "success")
        return redirect(url_for("index"))

    @app.get("/dashboard")
    @login_required
    def dashboard():
        return render_template("dashboard.html", user=g.user)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")
