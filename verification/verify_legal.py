import os
from playwright.sync_api import sync_playwright, expect

def verify_legal_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Load the local file
        file_path = os.path.abspath("docs/LEGAL.html")
        page.goto(f"file://{file_path}")

        # Verify Title
        expect(page).to_have_title("法律聲明與開源授權 - FlexiTools")

        # Verify Header
        header = page.locator("h1")
        expect(header).to_have_text("開源授權聲明")

        # Verify Project License Section
        license_section = page.locator(".glass-panel").first
        expect(license_section).to_contain_text("FlexiTools 授權")

        # Take a viewport screenshot instead of full page
        page.screenshot(path="verification/legal_page_viewport.png")
        print("Verification successful. Screenshot saved to verification/legal_page_viewport.png")

        browser.close()

if __name__ == "__main__":
    verify_legal_html()
