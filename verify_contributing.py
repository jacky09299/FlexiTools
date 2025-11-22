import os
from playwright.sync_api import sync_playwright, expect

def verify_contributing():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        repo_root = os.getcwd()
        file_path = os.path.join(repo_root, 'docs', 'CONTRIBUTING.html')
        url = f"file://{file_path}"

        print(f"Navigating to: {url}")
        page.goto(url)

        # Verify page title
        print("Verifying page title...")
        expect(page).to_have_title("FlexiTools - 開發者指南")

        # Verify main sections exist
        print("Verifying main sections...")
        expect(page.locator("#setup")).to_be_visible()
        expect(page.locator("#structure")).to_be_visible()
        expect(page.locator("#module-dev")).to_be_visible()
        expect(page.locator("#localization")).to_be_visible()
        expect(page.locator("#build")).to_be_visible()
        expect(page.locator("#submission")).to_be_visible()

        # Verify TOC sticky behavior (basic check existence)
        expect(page.locator(".toc-sticky")).to_be_visible()

        # Verify code blocks
        print("Verifying code blocks...")
        code_blocks = page.locator(".code-block")
        expect(code_blocks.first).to_be_visible()

        # Screenshot
        screenshot_path = "/home/jules/verification/contributing_page.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        browser.close()

if __name__ == "__main__":
    verify_contributing()