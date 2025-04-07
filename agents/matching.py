import sqlite3
import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from agents.job_summary import embedder  # NEW IMPORT
import os
def get_embedding_dimension():
    conn = sqlite3.connect("candidates.db")
    cursor = conn.cursor()
    cursor.execute("SELECT embedding FROM candidate_embeddings")
    for row in cursor.fetchall():
        emb = pickle.loads(row[0])
        if isinstance(emb, np.ndarray):
            conn.close()
            return len(emb)
    conn.close()
    raise ValueError("No valid embeddings found.")

def match_candidates(job_text, top_n=5):
    job_embedding = embedder(job_text)
    if isinstance(job_embedding, str):
        # Error string was returned
        print(job_embedding)
        return []

    job_embedding = np.array(job_embedding)


    BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # this will be /HireSmart-main/agents
    DB_PATH = os.path.join(BASE_DIR, "..", "candidates.db")  # go up one level

    conn = sqlite3.connect(os.path.abspath(DB_PATH))

    cursor = conn.cursor()
    cursor.execute("SELECT name, email, embedding FROM candidate_embeddings")
    rows = cursor.fetchall()

    results = []
    for name, email, emb_blob in rows:
        candidate_emb = pickle.loads(emb_blob)

        if len(candidate_emb) != len(job_embedding):
            print(f"⚠️ Skipping {name}: embedding shape mismatch")
            continue

        similarity = cosine_similarity([job_embedding], [candidate_emb])[0][0]
        similarity_percent = similarity * 100
    
        if similarity_percent >= 60.0:
            results.append((name, email, similarity_percent))

    conn.close()
    return sorted(results, key=lambda x: x[2], reverse=True)[:top_n]
