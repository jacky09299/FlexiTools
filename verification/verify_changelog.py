
from playwright.sync_api import sync_playwright

def verify_changelog():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the page served by python http server
        page.goto("http://localhost:8000/docs/download.html")

        # Wait for the version list to load
        page.wait_for_selector("#version-list li")

        # Check if v1.8.0 is present
        print("Checking for v1.8.0 text...")
        page.get_by_text("版本 v1.8.0").wait_for()

        # Check if the toggle button exists for the first item (v1.8.0)
        print("Looking for '顯示詳情' button...")
        button = page.get_by_text("顯示詳情").first

        # Click the button
        print("Clicking button...")
        button.click()

        # Wait for the collapse to show (bootstrap collapse adds 'show' class or expands height)
        # We can wait for the text inside the changelog to be visible
        print("Waiting for changelog text...")
        page.get_by_text("修正權限問題").wait_for(state="visible")

        # Take a screenshot
        screenshot_path = "verification/changelog_expanded.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        browser.close()

if __name__ == "__main__":
    verify_changelog()
