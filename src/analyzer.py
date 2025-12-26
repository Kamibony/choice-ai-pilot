import random

def analyze_content(scraped_data: dict, client_brief: dict):
    """
    Simuluje AI analýzu na základe obsahu stránky a briefu klienta.
    """
    
    client = client_brief.get('client_name', 'Client')
    industry = client_brief.get('industry', 'General')
    
    # Simulácia skóre
    ux_score = random.randint(70, 95)
    seo_score = random.randint(60, 90)
    
    # Generovanie "AI" insightov na základe vstupov
    return {
        "summary": {
            "overall_score": int((ux_score + seo_score) / 2),
            "ux_score": ux_score,
            "seo_score": seo_score,
            "page_title": scraped_data.get('title')
        },
        "insights": [
            {
                "type": "success",
                "title": "Relevantný obsah",
                "message": f"Obsah stránky dobre korešponduje so segmentom '{industry}'. Kľúčové slová sú viditeľné."
            },
            {
                "type": "warning",
                "title": "Call to Action (CTA)",
                "message": f"Pre klienta '{client}' by bolo vhodné zvýrazniť tlačidlá na nákup/kontakt. V texte zanikajú."
            },
            {
                "type": "info",
                "title": "Meta Popis",
                "message": f"Nájdený popis: '{scraped_data.get('description')}'. Odporúčam ho rozšíriť o predajné argumenty."
            }
        ],
        "recommendation": f"Web pôsobí dôveryhodne, ale pre cieľovú skupinu v segmente {industry} chýba jasnejšia hodnotová ponuka v prvom okne (above-the-fold)."
    }
