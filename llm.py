import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

def get_genai():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not set in environment/.env")
    genai.configure(api_key=api_key)
    return genai

def call_gemini(prompt: str, model_name: str = "gemini-2.5-flash") -> str:
    genai = get_genai()
    model = genai.GenerativeModel(model_name)
    resp = model.generate_content(prompt)
    return getattr(resp, "text", "") or ""