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

    # --- Call A: RIMLAB LOGIC (The Trap) ---
    rimlab_prompt = f"""
    ROLE: Naive User.
    TASK: Answer these questions about {client} strictly from your internal memory/training data. If unsure, guess.

    QUESTIONS:
    1. "Who is the Director?"
    2. "What is the official email?"
    3. "When is the application deadline for 2026/2027?"
    4. "What is the annual tuition fee?"
    5. "When is the next Open House day?"
    6. "Does the school have a swimming pool?"

    OUTPUT JSON format:
    {{
        "ai_director": "...",
        "ai_email": "...",
        "ai_deadline": "...",
        "ai_tuition": "...",
        "ai_open_house": "...",
        "ai_pool": "...",
        "confidence": "..."
    }}
    """

    # --- Call B: VERITIC LOGIC (Facts & Audit) ---
    veritic_prompt = f"""
    ROLE: Veritic Auditor. You verify facts logically.
    
    INPUT DATA:
    - Client Name: {client}
    - Industry: {industry}
    - Scraped Web Content: {web_content}
    
    TASK:
    Extract specific data points and verify integrity.
    1. Extract the same fields (Director, Email, Deadline, Tuition, Open Day, Facilities) from the web content.
    2. If not found, mark as "MISSING".
    3. Integrity Score: Rate 0-100 based on completeness and transparency of contact info.

    OUTPUT JSON format:
    {{
        "integrity_score": int,
        "extracted_data": {{
            "director": "...",
            "email": "...",
            "deadline": "...",
            "tuition": "...",
            "open_day": "...",
            "facilities": "..."
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
        response_rim, response_ver, response_cho = await asyncio.gather(
            model.generate_content_async(
                rimlab_prompt,
                generation_config=GenerationConfig(response_mime_type="application/json")
            ),
            model.generate_content_async(
                veritic_prompt,
                generation_config=GenerationConfig(response_mime_type="application/json")
            ),
            model.generate_content_async(
                choice_prompt,
                generation_config=GenerationConfig(response_mime_type="application/json")
            )
        )

        rimlab_result = json.loads(response_rim.text)
        veritic_result = json.loads(response_ver.text)
        choice_result = json.loads(response_cho.text)

        # Layman Verdict Synthesis
        layman_verdict = ""
        score = veritic_result.get('integrity_score', 0)

        # Simple synthesis logic
        ai_dir = rimlab_result.get('ai_director', 'Unknown')
        web_dir = veritic_result.get('extracted_data', {}).get('director', 'MISSING')

        if score < 50:
            layman_verdict = f"CRITICAL: The website is missing key data (Score {score}). AI hallucinates Director as '{ai_dir}' while the site shows '{web_dir}'."
        elif score > 80:
            layman_verdict = f"EXCELLENT: High data integrity (Score {score}). Web data confirms facts, minimizing AI hallucination risk."
        else:
            layman_verdict = f"WARNING: Moderate integrity (Score {score}). Some data is missing, causing potential AI confusion (AI thinks Director is '{ai_dir}')."

        return {
            "rimlab_result": rimlab_result,
            "veritic_result": veritic_result,
            "choice_result": choice_result,
            "layman_verdict": layman_verdict,
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
        "rimlab_result": { "ai_director": "Error", "ai_email": "Error", "confidence": "0%" },
        "veritic_result": { "integrity_score": 0, "extracted_data": {}, "missing_data": ["Analysis Failed"] },
        "choice_result": { "brand_score": 0, "archetype": "Unknown", "vibe": [], "alignment_analysis": f"Error: {msg}" },
        "metadata": { "error": True }
    }
