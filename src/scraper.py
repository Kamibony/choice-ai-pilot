from playwright.async_api import async_playwright

async def scrape_site(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Pre istotu emulujeme desktop, aby sme nedostali mobilnú verziu
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        try:
            print(f"Scraping URL: {url}")
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            # Získame kľúčové dáta
            title = await page.title()
            
            # Skúsime nájsť meta popis
            description = "No description found"
            try:
                description = await page.locator('meta[name="description"]').get_attribute("content")
            except:
                pass

            # Získame čistý text (pre AI analýzu)
            body_text = await page.locator('body').inner_text()
            
            await browser.close()
            
            return {
                "url": url,
                "title": title,
                "description": description,
                "content_preview": body_text[:5000] # Limit pre demo
            }
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            await browser.close()
            return None
