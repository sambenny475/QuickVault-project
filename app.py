from importlib.resources import files

from flask import Flask, flash, render_template, request, redirect, session, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db():
    return sqlite3.connect('vault.db')


# Create tables
def init_db():
    conn = get_db()

    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        phone TEXT,
        password TEXT
    )
    ''')

    conn.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        filename TEXT
    )
    ''')

    conn.close()


init_db()


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']

        conn = get_db()
        conn.execute(
            "INSERT INTO users (phone, password) VALUES (?, ?)",
            (phone, password)
        )
        conn.commit()
        conn.close()

        return redirect('/')

    return render_template('register.html')

# LOGIN


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE phone=?",
            (phone,)
        ).fetchone()

        if user:
            if user[2] == password:
                session['user_id'] = user[0]
                conn.close()
                return redirect('/dashboard')
            else:
                conn.close()
                flash("wrong password")
                return redirect('/')
        else:
            conn.close()
            flash("User not found")
            return redirect('/')

    return render_template('login.html')


#  DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')

    conn = get_db()
    files = conn.execute(
        "SELECT * FROM files WHERE user_id=?",
        (session['user_id'],)
    ).fetchall()
    conn.close()

    return render_template('dashboard.html', files=files)


# UPLOAD
@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session:
        return redirect('/')

    files = request.files.getlist('file')
    conn = get_db()

    for file in files:
        if file and file.filename != "":
            filename = secure_filename(file.filename)

            # CHECK DUPLICATE IN DB
            existing = conn.execute(
                "SELECT * FROM files WHERE user_id=? AND filename=?",
                (session['user_id'], filename)
            ).fetchone()

            if existing:
                flash(f"{filename} already exists")
                continue  # skip duplicate

            # Save file
            file.save(os.path.join(UPLOAD_FOLDER, filename))

            # Save in DB
            conn.execute(
                "INSERT INTO files (user_id, filename) VALUES (?, ?)",
                (session['user_id'], filename)
            )

    conn.commit()
    conn.close()

    return redirect('/dashboard')


# DOWNLOAD
@app.route('/files/<filename>')
def files(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# 🗑 DELETE
@app.route('/delete/<int:file_id>')
def delete(file_id):
    conn = get_db()

    file = conn.execute(
        "SELECT filename FROM files WHERE id=?",
        (file_id,)
    ).fetchone()

    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file[0])

        # Delete file from folder safely
        if os.path.exists(filepath):
            os.remove(filepath)

        # ALWAYS delete from DB
        conn.execute(
            "DELETE FROM files WHERE id=?",
            (file_id,)
        )
        conn.commit()
    print("Deleting:", files)
    conn.close()
    return redirect('/dashboard')


if __name__ == '__main__':
    app.run(debug=True)
