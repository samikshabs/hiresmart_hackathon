from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import numpy as np
from agents.job_summary import generate_summary_with_llama3
from agents.matching import match_candidates, get_embedding_dimension
from utils.email_sender import send_interview_email
import pickle
app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

APP_DB = 'app.db'
CANDIDATE_DB = 'candidates.db'

# ------------------- INIT DB -------------------

def init_app_db():
    conn = sqlite3.connect(APP_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    email TEXT,
                    password TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    description TEXT,
                    summary TEXT,
                    embedding BLOB
                )''')
    conn.commit()
    conn.close()

def init_candidate_db():
    conn = sqlite3.connect(CANDIDATE_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS interview_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_email TEXT NOT NULL,
                    interview_datetime TEXT NOT NULL
                )''')
    conn.commit()
    conn.close()

init_app_db()
init_candidate_db()

# ------------------- ROUTES -------------------

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(APP_DB)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                      (username, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists."
        conn.close()
        return redirect(url_for('signin'))
    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(APP_DB)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['username'] = user[1]
            return redirect(url_for('job_summary'))
        else:
            return "Invalid credentials"
    return render_template('signin.html')

from agents.job_summary import embedder  # Add this if not already

@app.route('/job_summary', methods=['GET', 'POST'])
def job_summary():
    title = ''
    description = ''
    summary = ''
    responsibilities = ''
    skills = ''
    experience = ''
    qualification = ''

    if request.method == 'POST':
        try:
            title = request.form['title']
            description = request.form['job_description']
            raw_summary = generate_summary_with_llama3(title, description)

            def extract_section(label, text):
                start = text.find(label)
                if start == -1:
                    return ""
                start += len(label)
                next_labels = [
                    "Responsibilities:", "Skills Required:",
                    "Experience:", "Qualifications:", "Job Summary:"
                ]
                next_labels.remove(label)
                next_positions = [text.find(l) for l in next_labels if text.find(l) > start]
                end = min(next_positions) if next_positions else len(text)
                return text[start:end].strip()

            responsibilities = extract_section("Responsibilities:", raw_summary)
            skills = extract_section("Skills Required:", raw_summary)
            experience = extract_section("Experience:", raw_summary)
            qualification = extract_section("Qualifications:", raw_summary)
            summary = extract_section("Job Summary:", raw_summary)

            # 🔥 Get and save embedding to DB
            job_text = f"{title}. {description}"
            embedding = embedder(job_text)
            if isinstance(embedding, str):
                raise ValueError(embedding)
            emb_blob = pickle.dumps(np.array(embedding))

            conn = sqlite3.connect(APP_DB)
            c = conn.cursor()
            c.execute("INSERT INTO jobs (title, description, summary, embedding) VALUES (?, ?, ?, ?)",
                      (title, description, summary, emb_blob))
            conn.commit()
            conn.close()

        except Exception as e:
            summary = f"Error processing request: {e}"

    return render_template(
        'job_summary.html',
        title=title,
        original=description,
        summary=summary,
        responsibilities=responsibilities,
        skills=skills,
        experience=experience,
        qualification=qualification
    )

@app.route('/result', methods=['GET', 'POST'])
def result():
    conn = sqlite3.connect(APP_DB)
    c = conn.cursor()
    c.execute("SELECT title, description FROM jobs ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()

    if row:
        job_text = f"{row[0]}. {row[1]}"
        top_matches = match_candidates(job_text)
    else:
        top_matches = []

    return render_template('result.html', matches=top_matches)


@app.route('/schedule_interview/<email>', methods=['GET', 'POST'])
def schedule_interview(email):
    if request.method == 'POST':
        date = request.form['date']
        time = request.form['time']
        dt = f"{date} {time}"

        # Save to database
        conn = sqlite3.connect(CANDIDATE_DB)
        c = conn.cursor()
        c.execute('''INSERT INTO interview_schedule (candidate_email, interview_datetime) 
                     VALUES (?, ?)''', (email, dt))
        conn.commit()
        conn.close()

        meeting_link = f"https://zoom.com/meet/{email.split('@')[0]}"

        # Optionally extract name from email or pass a static one
        name = email.split('@')[0].capitalize()  # You can also query name if stored

        # Send confirmation email
        send_interview_email(name, email, dt)

        message = f"Email has been sent to {name} at {email}."
        return render_template("confirmation.html", email=email, dt=dt, link=meeting_link, message=message)

    return render_template("schedule_form.html", email=email)

# ------------------- START -------------------

if __name__ == '__main__':
    app.run(debug=True)