from playwright.sync_api import sync_playwright, expect

def verify_uml():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Capture console logs
        page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"Browser Error: {exc}"))

        print("Navigating to UML page...")
        page.goto("http://localhost:8080/docs/uml.html")

        print("Waiting for nodes...")
        try:
            page.wait_for_selector(".uml-class", timeout=5000)
            print("Nodes found.")
        except Exception as e:
            print(f"Nodes not found: {e}")

        # Give a little time for layout engine to run (setTimeout 100ms in the code)
        page.wait_for_timeout(2000)

        print("Checking content...")
        try:
            expect(page.get_by_text("ModularGUI")).to_be_visible()
            print("ModularGUI visible.")
        except Exception as e:
            print(f"ModularGUI check failed: {e}")

        print("Checking SVG connections...")
        count = page.locator("svg#connections path").count()
        print(f"Found {count} SVG paths.")

        # Take screenshot regardless of success to debug
        screenshot_path = "verification_uml.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        assert count > 0, "No SVG paths found for connections."

        browser.close()

if __name__ == "__main__":
    verify_uml()
