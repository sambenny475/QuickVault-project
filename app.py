from flask import Flask, flash, render_template, request, redirect, session, send_from_directory
import psycopg2
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    return psycopg2.connect(DATABASE_URL)


# 🔥 INIT DB
def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        phone TEXT UNIQUE,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        filename TEXT
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


# 🔥 REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users (phone, password) VALUES (%s, %s)",
                (phone, password)
            )
            conn.commit()
        except:
            flash("User already exists")

        cur.close()
        conn.close()

        return redirect('/')

    return render_template('register.html')


# 🔐 LOGIN
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE phone=%s",
            (phone,)
        )

        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:
            if user[2] == password:
                session['user_id'] = user[0]
                return redirect('/dashboard')
            else:
                flash("Wrong password")
        else:
            flash("User not found")

        return redirect('/')

    return render_template('login.html')


# 📁 DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM files WHERE user_id=%s",
        (session['user_id'],)
    )

    files = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('dashboard.html', files=files)


# 📤 UPLOAD
@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session:
        return redirect('/')

    files = request.files.getlist('file')

    conn = get_db()
    cur = conn.cursor()

    for file in files:
        if file and file.filename != "":
            filename = secure_filename(file.filename)

            # 🔥 CHECK DUPLICATE
            cur.execute(
                "SELECT * FROM files WHERE user_id=%s AND filename=%s",
                (session['user_id'], filename)
            )
            existing = cur.fetchone()

            if existing:
                flash(f"{filename} already exists")
                continue

            # Save file
            file.save(os.path.join(UPLOAD_FOLDER, filename))

            # Save in DB
            cur.execute(
                "INSERT INTO files (user_id, filename) VALUES (%s, %s)",
                (session['user_id'], filename)
            )

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/dashboard')


# 📥 DOWNLOAD
@app.route('/files/<filename>')
def files(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# 🗑 DELETE
@app.route('/delete/<int:file_id>')
def delete(file_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT filename FROM files WHERE id=%s",
        (file_id,)
    )
    file = cur.fetchone()

    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file[0])

        if os.path.exists(filepath):
            os.remove(filepath)

        cur.execute(
            "DELETE FROM files WHERE id=%s",
            (file_id,)
        )
        conn.commit()

    cur.close()
    conn.close()

    return redirect('/dashboard')


# 🔥 RUN INIT
init_db()

if __name__ == '__main__':
    app.run(debug=True)
