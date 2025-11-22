import os
from playwright.sync_api import sync_playwright, expect

def verify_tutorials():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        repo_root = os.getcwd()
        file_path = os.path.join(repo_root, 'docs', 'tutorials.html')
        url = f"file://{file_path}"

        print(f"Navigating to: {url}")
        page.goto(url)

        # 1. Verify General Usage Section
        print("Verifying General Usage...")
        general_usage = page.locator("#general-usage")
        expect(general_usage).to_be_visible()

        # Check for one of the new feature cards
        feature_card = page.get_by_text("介面概覽")
        expect(feature_card).to_be_visible()

        # 2. Verify Exe Embedder Card exists
        print("Verifying Exe Embedder Card...")
        # The card title is "Exe Embedder"
        exe_card = page.locator(".module-card").filter(has_text="Exe Embedder")
        expect(exe_card).to_be_visible()

        # 3. Open Modal
        print("Opening Modal...")
        exe_card.click()

        # Wait for modal to be visible
        modal = page.locator("#tutorialModal")
        expect(modal).to_be_visible()

        # Wait for animation
        page.wait_for_timeout(1000)

        # 4. Screenshot
        screenshot_path = "/home/jules/verification/tutorials_modal.png"
        page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")

        browser.close()

if __name__ == "__main__":
    verify_tutorials()