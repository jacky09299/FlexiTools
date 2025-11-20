from playwright.sync_api import sync_playwright, expect

def test_uml_page_and_footer():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Check Index Footer Link
        print("Checking index.html footer...")
        page.goto("http://localhost:8080/docs/index.html")

        # Scroll to bottom
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        # Check for the UML link
        uml_link = page.get_by_role("link", name="UML 架構圖")
        expect(uml_link).to_be_visible()

        # Take screenshot of footer
        page.screenshot(path="verification/index_footer.png")
        print("Captured index_footer.png")

        # 2. Check UML Page
        print("Checking uml.html...")
        # Click the link to go to UML page
        uml_link.click()

        # Wait for UML page to load
        page.wait_for_url("**/docs/uml.html")
        expect(page).to_have_title("FlexiTools - UML 架構圖")

        # Wait for canvas and nodes (loading might take a moment)
        page.wait_for_selector("#nodes-container .uml-class", timeout=5000)

        # Verify Navbar is present
        expect(page.get_by_role("navigation")).to_be_visible()

        # Verify Controls are present
        expect(page.locator("#controls")).to_be_visible()

        # Verify Footer is present (at the bottom)
        # We can check if it is visible
        expect(page.locator("footer")).to_be_visible()

        # Take screenshot of the UML page
        page.screenshot(path="verification/uml_page.png")
        print("Captured uml_page.png")

        browser.close()

if __name__ == "__main__":
    test_uml_page_and_footer()
