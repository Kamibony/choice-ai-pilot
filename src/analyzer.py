import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import json
import os

# Inicializácia Vertex AI (automaticky použije vaše Google Cloud credentials)
# PROJECT_ID sa na Cloud Run nastaví automaticky, ale pre istotu ho čítame z env
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = "us-central1" # Vertex AI je najstabilnejší v US

try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
except Exception as e:
    print(f"Warning: Vertex AI init failed (local run?): {e}")

def analyze_content(scraped_data: dict, client_brief: dict):
    """
    Odošle dáta do Gemini a získa skutočnú analýzu.
    """
    
    # 1. Príprava modelu
    model = GenerativeModel("gemini-1.5-flash-001") # Používame Flash pre rýchlosť
    
    # 2. Vytvorenie Promptu (inštrukcií pre AI)
    # Hovoríme AI, aby sa správala ako API a vrátila len čistý JSON.
    prompt = f"""
    You are a Senior UX & Marketing Auditor. Analyze the following website content based on the client brief.
    
    CLIENT BRIEF:
    - Client Name: {client_brief.get('client_name')}
    - Industry: {client_brief.get('industry')}
    - Goals: {client_brief.get('goals')}
    
    WEBSITE DATA (Scraped):
    - URL: {scraped_data.get('url')}
    - Title: {scraped_data.get('title')}
    - Description: {scraped_data.get('description')}
    - Content Preview: {scraped_data.get('content_preview')}... (truncated)

    TASK:
    Analyze the website and provide a structured JSON response. Do NOT use Markdown formatting.
    Evaluate:
    1. UX Score (0-100) based on clarity and structure.
    2. SEO Score (0-100) based on keywords and meta tags.
    3. 3 specific insights (Success, Warning, Info).
    4. One strategic recommendation.

    OUTPUT FORMAT (JSON ONLY):
    {{
        "summary": {{
            "overall_score": int,
            "ux_score": int,
            "seo_score": int,
            "page_title": "string"
        }},
        "insights": [
            {{ "type": "success", "title": "string", "message": "string" }},
            {{ "type": "warning", "title": "string", "message": "string" }},
            {{ "type": "info", "title": "string", "message": "string" }}
        ],
        "recommendation": "string"
    }}
    """

    print("Sending request to Gemini...")
    
    try:
        # 3. Volanie AI
        response = model.generate_content(
            prompt,
            generation_config=GenerationConfig(response_mime_type="application/json")
        )
        
        # 4. Spracovanie odpovede
        json_response = json.loads(response.text)
        return json_response

    except Exception as e:
        print(f"Error calling Gemini: {e}")
        # Fallback pre prípad chyby (aby appka nepadla)
        return {
            "summary": { "overall_score": 0, "ux_score": 0, "seo_score": 0, "page_title": "Error in Analysis" },
            "insights": [{ "type": "warning", "title": "AI Error", "message": "Nepodarilo sa spojiť s AI modelom. Skontrolujte kvóty." }],
            "recommendation": "Skúste to prosím neskôr."
        }
