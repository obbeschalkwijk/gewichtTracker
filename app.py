from datetime import datetime, timedelta
import os
import sqlite3

from flask import Flask, jsonify, redirect, render_template, request, url_for

app = Flask(__name__)

DB_PATH = "weights.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_weight(value):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None

    if parsed <= 0 or parsed > 500:
        return None
    return parsed


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


@app.route("/")
def index():
    conn = get_db_connection()
    weights = conn.execute("SELECT * FROM weights ORDER BY date DESC").fetchall()

    last_weight_row = conn.execute(
        "SELECT weight FROM weights ORDER BY date DESC LIMIT 1"
    ).fetchone()
    last_weight = last_weight_row["weight"] if last_weight_row else 70.0

    today_1 = datetime.today().strftime("%Y-%m-%d")

    week_ago = datetime.now() - timedelta(days=7)
    avg_query = conn.execute(
        "SELECT AVG(weight) as avg_weight FROM weights WHERE date >= ?",
        (week_ago.strftime("%Y-%m-%d"),),
    ).fetchone()
    avg_weight = avg_query["avg_weight"] if avg_query["avg_weight"] else 0
    conn.close()

    return render_template(
        "index.html",
        last_weight=last_weight,
        today_1=today_1,
        weights=weights,
        avg_weight=avg_weight,
    )


@app.route("/add", methods=["POST"])
def add_weight():
    weight = parse_weight(request.form.get("weight"))
    date = request.form.get("date")

    if parse_date(date) is None:
        return jsonify({"status": "error", "message": "Invalid date format"}), 400
    if weight is None:
        return jsonify({"status": "error", "message": "Invalid weight"}), 400

    conn = get_db_connection()
    conn.execute(
        "INSERT OR REPLACE INTO weights (date, weight) VALUES (?, ?)", (date, weight)
    )
    conn.commit()

    week_ago = datetime.now() - timedelta(days=7)
    avg_query = conn.execute(
        "SELECT AVG(weight) as avg_weight FROM weights WHERE date >= ?",
        (week_ago.strftime("%Y-%m-%d"),),
    ).fetchone()
    avg_weight = avg_query["avg_weight"] if avg_query["avg_weight"] else 0

    conn.close()
    return jsonify({"status": "success", "avg_weight": round(avg_weight, 1)})


@app.route("/data", methods=["GET"])
def get_data():
    scale = request.args.get("scale", "week")
    today = datetime.now()

    if scale == "week":
        start_date = today - timedelta(days=7)
    elif scale == "month":
        start_date = today - timedelta(days=31)
    elif scale == "year":
        start_date = today - timedelta(days=365)
    else:
        return jsonify({"error": "Invalid scale"}), 400

    conn = get_db_connection()
    data = conn.execute(
        "SELECT date, weight FROM weights WHERE date >= ? ORDER BY date ASC",
        (start_date.strftime("%Y-%m-%d"),),
    ).fetchall()
    conn.close()

    return jsonify([{"date": row["date"], "weight": row["weight"]} for row in data])


@app.route("/weights", methods=["GET", "POST"])
def weights():
    conn = get_db_connection()

    if request.method == "POST" and "delete" in request.form:
        weight_id = request.form["delete"]
        conn.execute("DELETE FROM weights WHERE id = ?", (weight_id,))
        conn.commit()
        conn.close()
        return redirect(url_for("weights"))

    rows = conn.execute("SELECT * FROM weights ORDER BY date DESC").fetchall()
    conn.close()

    return render_template("weights.html", weights=rows)


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_weight(id):
    conn = get_db_connection()

    if request.method == "POST":
        new_weight = parse_weight(request.form.get("weight"))
        new_date = request.form.get("date")

        if parse_date(new_date) is None or new_weight is None:
            conn.close()
            return jsonify({"status": "error", "message": "Invalid form input"}), 400

        conn.execute(
            "UPDATE weights SET weight = ?, date = ? WHERE id = ?",
            (new_weight, new_date, id),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("weights"))

    row = conn.execute("SELECT * FROM weights WHERE id = ?", (id,)).fetchone()
    conn.close()

    return render_template("edit_weight.html", weight=row)


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
