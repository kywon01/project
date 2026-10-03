import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

DB_PATH = Path(__file__).parent / "todos.db"
PRIORITIES = ("low", "medium", "high")

app = Flask(__name__)
CORS(app)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                due_date TEXT,
                priority TEXT NOT NULL DEFAULT 'medium',
                category TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(todos)")}
        if "due_date" not in existing_columns:
            conn.execute("ALTER TABLE todos ADD COLUMN due_date TEXT")
        if "priority" not in existing_columns:
            conn.execute("ALTER TABLE todos ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium'")
        if "category" not in existing_columns:
            conn.execute("ALTER TABLE todos ADD COLUMN category TEXT")


@app.route("/api/todos", methods=["GET"])
def list_todos():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    priority = request.args.get("priority", "").strip()

    query = "SELECT * FROM todos WHERE 1=1"
    params = []
    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")
    if category:
        query += " AND category = ?"
        params.append(category)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    query += " ORDER BY id DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return jsonify([dict(row) for row in rows])


@app.route("/api/categories", methods=["GET"])
def list_categories():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM todos WHERE category IS NOT NULL AND category != '' ORDER BY category"
        ).fetchall()
    return jsonify([row["category"] for row in rows])


@app.route("/api/todos", methods=["POST"])
def create_todo():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    priority = (data.get("priority") or "medium").strip()
    if priority not in PRIORITIES:
        return jsonify({"error": f"priority must be one of {PRIORITIES}"}), 400

    due_date = (data.get("due_date") or "").strip() or None
    category = (data.get("category") or "").strip() or None

    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO todos (title, due_date, priority, category) VALUES (?, ?, ?, ?)",
            (title, due_date, priority, category),
        )
        todo_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/todos/<int:todo_id>", methods=["PUT"])
def update_todo(todo_id):
    data = request.get_json(silent=True) or {}

    with get_db() as conn:
        existing = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "todo not found"}), 404

        title = data.get("title", existing["title"])
        done = data.get("done", existing["done"])
        due_date = data.get("due_date", existing["due_date"])
        category = data.get("category", existing["category"])

        priority = data.get("priority", existing["priority"])
        if priority not in PRIORITIES:
            return jsonify({"error": f"priority must be one of {PRIORITIES}"}), 400

        conn.execute(
            "UPDATE todos SET title = ?, done = ?, due_date = ?, priority = ?, category = ? WHERE id = ?",
            (title, int(bool(done)), due_date, priority, category, todo_id),
        )
        row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    return jsonify(dict(row))


@app.route("/api/todos/<int:todo_id>", methods=["DELETE"])
def delete_todo(todo_id):
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
        if existing is None:
            return jsonify({"error": "todo not found"}), 404
        conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    return "", 204


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
