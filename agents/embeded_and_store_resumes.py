""" dont exexute this file """

import sqlite3
import pickle
import os
os.environ["OLLAMA_HOST"] = "http://localhost:11434"
import numpy as np
from PyPDF2 import PdfReader
from ollama import chat
import re
from ollama import Client

client = Client(host="http://localhost:11434")



# === CONFIG ===
DB_PATH = "candidates.db"
RESUME_FOLDER = "HireSmart-main\CVs1"  # new folder with remaining resumes
FIELD_MODEL = "mistral"  # model for field extraction
EMBED_MODEL = "all-MiniLM-L6-v2"  # embedding model
import os

# === DB SETUP ===
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS candidate_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    phone TEXT,
    responsibilities TEXT,
    skills TEXT,
    qualifications TEXT,
    experience TEXT,
    embedding BLOB
)
""")

# === UTILS ===
def already_processed(email):
    cursor.execute("SELECT 1 FROM candidate_embeddings WHERE email = ?", (email,))
    return cursor.fetchone() is not None

# === EXTRACT TEXT FROM PDF ===
def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        text = text.encode("utf-8", "ignore").decode()
        return text.strip()
    except Exception as e:
        print(f"❌ Error reading {pdf_path}: {e}")
        return ""

# === PROMPT FOR STRUCTURED FIELDS ===
def extract_fields(text):
    prompt = f"""
You are an assistant that extracts structured data from resumes. Given the resume below, extract and return the following:

- Name
- Email
- Phone
- Responsibilities
- Skills
- Qualifications
- Experience

Return the data in this format:

Name: ...
Email: ...
Phone: ...
Responsibilities: ...
Skills: ...
Qualifications: ...
Experience: ...

Resume:
{text}
""".strip()

    try:
        response = client.chat(model=FIELD_MODEL, messages=[{"role": "user", "content": prompt}])
        content = response["message"]["content"]
    except Exception as e:
        print(f"❌ Error from Ollama model {FIELD_MODEL}: {e}")
        return {}

    def extract(label):
        match = re.search(rf'{label}:\s*(.*?)(?=\n\S+:|$)', content, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    return {
        "name": extract("Name"),
        "email": extract("Email"),
        "phone": extract("Phone"),
        "responsibilities": extract("Responsibilities"),
        "skills": extract("Skills"),
        "qualifications": extract("Qualifications"),
        "experience": extract("Experience")
    }

from sentence_transformers import SentenceTransformer

# Load SentenceTransformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text):
    try:
        return model.encode(text).tolist()
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return None


# === MAIN LOOP ===
for filename in os.listdir(RESUME_FOLDER):
    if not filename.endswith(".pdf"):
        continue

    pdf_path = os.path.join(RESUME_FOLDER, filename)
    print(f"\n📄 Processing {filename}...")

    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text:
        print("❌ Skipping due to unreadable text.")
        continue

    fields = extract_fields(raw_text)
    if not fields.get("name") or not fields.get("email"):
        print("❌ Skipping due to missing name/email.")
        continue

    if already_processed(fields["email"]):
        print("⚠️ Already embedded. Skipping.")
        continue

    concat_for_embedding = " ".join([
        fields["responsibilities"],
        fields["skills"],
        fields["qualifications"],
        fields["experience"]
    ]).strip()

    if not concat_for_embedding:
        print("❌ Skipping due to empty content for embedding.")
        continue

    embedding = get_embedding(concat_for_embedding)
    if embedding is None:
        print("❌ Skipping due to embedding failure.")
        continue

    embedding_blob = pickle.dumps(embedding)

    cursor.execute("""
    INSERT INTO candidate_embeddings (name, email, phone, responsibilities, skills, qualifications, experience, embedding)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        fields["name"],
        fields["email"],
        fields["phone"],
        fields["responsibilities"],
        fields["skills"],
        fields["qualifications"],
        fields["experience"],
        embedding_blob
    ))
    conn.commit()
    print("✅ Stored.")

conn.close()