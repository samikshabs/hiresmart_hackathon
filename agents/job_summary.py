import requests
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# === Lazy Load + Cache the Model ===
_model = None

def embedder(text):
    global _model
    try:
        if _model is None:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('all-MiniLM-L6-v2')
        embedding = _model.encode(text, convert_to_numpy=True)
        return embedding.tolist()  # Convert to list for JSON serialization
    except Exception as e:
        return f"❌ Error generating embedding: {e}"

# === 1. Generate Job Summary using LLaMA-3 ===
def generate_summary_with_llama3(title, description):
    api_key = os.getenv("OPENROUTER_API_KEY")
    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    
    prompt = f"""
You are an AI assistant that extracts structured information from job descriptions.

Given the following Job Title and Job Description, extract the key details and provide them in the following format:

Job Title: <title>
Responsibilities: <bullet points>
Skills Required: <bullet points or comma-separated list>
Experience: <summary of experience requirements>
Qualifications: <summary of education/certifications needed>
Job Summary: <3–5 line concise summary of the job>

Job Title: {title}
Job Description: {description}
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",  # optional
    }

    data = {
        "model": "meta-llama/llama-3-8b-instruct",
        "messages": [
            {"role": "user", "content": prompt.strip()}
        ]
    }

    try:
        response = requests.post(endpoint, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Error generating summary: {e}"
