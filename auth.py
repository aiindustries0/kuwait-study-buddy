import sqlite3
from functools import wraps

from flask import flash, g, redirect, request, url_for
from werkzeug.security import check_password_hash, generate_password_hash


def get_db(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(database_path):
    connection = get_db(database_path)
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
    finally:
        connection.close()


def get_user_by_id(database_path, user_id):
    connection = get_db(database_path)
    try:
        return connection.execute("SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        connection.close()


def create_user(database_path, name, email, password):
    connection = get_db(database_path)
    try:
        connection.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", (name, email, generate_password_hash(password)))
        connection.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        connection.close()


def authenticate_user(database_path, email, password):
    connection = get_db(database_path)
    try:
        user = connection.execute("SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    finally:
        connection.close()
    if user is None or not check_password_hash(user["password_hash"], password):
        return None
    return user


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please log in to open your study dashboard.", "error")
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view
