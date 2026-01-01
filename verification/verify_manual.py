from playwright.sync_api import sync_playwright, expect

def verify_manual_modal():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:8000")

        # Open manual modal
        page.click("button:has-text('📘 Nápověda')")

        # Wait for modal to be visible
        modal = page.locator("#manualModal")
        expect(modal).to_be_visible()

        # Check RimLab section
        rimlab_text = modal.locator("text=Sleduje 6 bodů: Ředitel, Email, Termín, Školné, DOD, Bazén").first
        expect(rimlab_text).to_be_visible()

        # Check Synthesis section
        synthesis_header = modal.locator("h3:has-text('🧠 Syntéza & Interpretace')")
        expect(synthesis_header).to_be_visible()

        synthesis_desc = modal.locator("text=Finální verdikt na spodku karty. Porovnává AI halucinace vs. Realitu webu a hodnotí důvěryhodnost.")
        expect(synthesis_desc).to_be_visible()

        # Take screenshot
        page.screenshot(path="verification/manual_modal.png")
        print("Verification successful, screenshot saved.")

        browser.close()

if __name__ == "__main__":
    verify_manual_modal()
