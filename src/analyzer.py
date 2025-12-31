import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import json
import os
import time
import asyncio

# Konfigurácia (Európa)
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = "europe-west1" 

try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
except Exception as e:
    print(f"Warning: Vertex AI init failed: {e}")

async def analyze_universal(scraped_data: dict, client_brief: dict):
    """
    Dual-Mode Analysis: Veritic (Logic) & Choice (Emotion).
    """
    
    try:
        model = GenerativeModel("gemini-2.5-pro")
    except Exception as e:
        return _error_response(str(e))
    
    client = client_brief.get('client_name')
    goals = client_brief.get('goals')
    industry = client_brief.get('industry')
    web_content = scraped_data.get('content_preview', '')[:5000] # Limit content size
    
    print(f"--- STARTING UNIVERSAL ANALYSIS FOR: {client} ---")

    # --- Call A: VERITIC LOGIC (Facts & Audit) ---
    veritic_prompt = f"""
    ROLE: Veritic Auditor. You verify facts logically.
    
    INPUT DATA:
    - Client Name: {client}
    - Industry: {industry}
    - Scraped Web Content: {web_content}
    
    TASK:
    Extract specific data points and verify integrity.
    1. Extract: Email, Phone, Director/CEO, Opening Hours.
    2. Check Missing Data: What crucial contact info is missing?
    3. Integrity Score: Rate 0-100 based on completeness and transparency of contact info.

    OUTPUT JSON format:
    {{
        "integrity_score": int,
        "extracted_data": {{
            "email": "...",
            "phone": "...",
            "director": "...",
            "hours": "..."
        }},
        "missing_data": ["list", "of", "missing", "items"]
    }}
    """

    # --- Call B: CHOICE LOGIC (Brand & Emotion) ---
    choice_prompt = f"""
    ROLE: Brand Psychologist. You analyze emotional resonance and archetype.
    
    INPUT DATA:
    - Client Name: {client}
    - Stated Goals: {goals}
    - Scraped Web Content: {web_content}

    TASK:
    Analyze the brand's soul.
    1. Identify Brand Archetype (e.g., Hero, Sage, Caregiver).
    2. Analyze Sentiment/Vibe (3 adjectives).
    3. Alignment Score: Rate 0-100 on how well the web content matches the Stated Goals.

    OUTPUT JSON format:
    {{
        "brand_score": int,
        "archetype": "...",
        "vibe": ["adj1", "adj2", "adj3"],
        "alignment_analysis": "Short comment on goals vs reality."
    }}
    """

    # Execute Parallel Calls
    try:
        response_a, response_b = await asyncio.gather(
            model.generate_content_async(
                veritic_prompt,
                generation_config=GenerationConfig(response_mime_type="application/json")
            ),
            model.generate_content_async(
                choice_prompt,
                generation_config=GenerationConfig(response_mime_type="application/json")
            )
        )

        veritic_result = json.loads(response_a.text)
        choice_result = json.loads(response_b.text)

        return {
            "veritic_result": veritic_result,
            "choice_result": choice_result,
            "metadata": {
                "client": client,
                "url": scraped_data.get('url', 'N/A')
            }
        }

    except Exception as e:
        print(f"Analysis Error: {e}")
        return _error_response(str(e))

def _error_response(msg):
    return {
        "veritic_result": { "integrity_score": 0, "extracted_data": {}, "missing_data": ["Analysis Failed"] },
        "choice_result": { "brand_score": 0, "archetype": "Unknown", "vibe": [], "alignment_analysis": f"Error: {msg}" },
        "metadata": { "error": True }
    }
