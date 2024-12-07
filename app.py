from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

DB_PATH = 'weights.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn



@app.route('/')
def index():
    conn = get_db_connection()
    weights = conn.execute('SELECT * FROM weights ORDER BY date DESC').fetchall()

    # Haal het laatste gewicht op, gesorteerd op datum
    last_weight = conn.execute('SELECT weight FROM weights ORDER BY date DESC LIMIT 1').fetchone()


    # Als er geen gewichten zijn ingevuld, stel een standaardgewicht in (bijvoorbeeld 70.0)
    last_weight = last_weight['weight'] if last_weight else 70.0

    # Geef het gewicht en de huidige datum door aan de template
    today_1 = datetime.today().strftime('%Y-%m-%d')


    # Bereken 7-dagen gemiddelde
    today = datetime.now()
    week_ago = today - timedelta(days=7)

    avg_query = conn.execute(
        'SELECT AVG(weight) as avg_weight FROM weights WHERE date >= ?',
        (week_ago.strftime('%Y-%m-%d'),)
    ).fetchone()
    avg_weight = avg_query['avg_weight'] if avg_query['avg_weight'] else 0
    conn.close()

    return render_template('index.html', last_weight=last_weight, today_1=today_1, weights=weights, avg_weight=avg_weight)


@app.route('/add', methods=['POST'])
def add_weight():
    weight = request.form['weight']
    date = request.form['date']

    try:
        # Controleer of de datum geldig is
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format'}), 400

    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO weights (date, weight) VALUES (?, ?)', (date, weight))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})

@app.route('/data', methods=['GET'])
def get_data():
    scale = request.args.get('scale', 'week')  # standaard 'week'
    today = datetime.now()
    
    if scale == 'week':
        start_date = today - timedelta(days=7)
    elif scale == 'month':
        start_date = today - timedelta(days=31)
    elif scale == 'year':
        start_date = today - timedelta(days=365)
    else:
        return jsonify({'error': 'Invalid scale'}), 400

    conn = get_db_connection()
    data = conn.execute(
        'SELECT date, weight FROM weights WHERE date >= ? ORDER BY date ASC',
        (start_date.strftime('%Y-%m-%d'),)
    ).fetchall()
    conn.close()

    return jsonify([{'date': row['date'], 'weight': row['weight']} for row in data])


@app.route('/weights', methods=['GET', 'POST'])
def weights():
    conn = get_db_connection()
    
    # Als de gebruiker een gewicht wil verwijderen
    if request.method == 'POST' and 'delete' in request.form:
        weight_id = request.form['delete']
        conn.execute('DELETE FROM weights WHERE id = ?', (weight_id,))
        conn.commit()
        return redirect(url_for('weights'))

    # Haal alle gewichten uit de database
    rows = conn.execute('SELECT * FROM weights ORDER BY date DESC').fetchall()
    conn.close()

    return render_template('weights.html', weights=rows)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_weight(id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        new_weight = request.form['weight']
        new_date = request.form['date']
        conn.execute('UPDATE weights SET weight = ?, date = ? WHERE id = ?', (new_weight, new_date, id))
        conn.commit()
        return redirect(url_for('weights'))

    # Haal het gewicht op dat bewerkt moet worden
    row = conn.execute('SELECT * FROM weights WHERE id = ?', (id,)).fetchone()
    conn.close()

    return render_template('edit_weight.html', weight=row)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
