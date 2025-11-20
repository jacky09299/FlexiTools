from playwright.sync_api import sync_playwright, expect

def test_about_page_developers_section():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Go to About Page
        print("Checking about.html...")
        page.goto("http://localhost:8080/docs/about.html")

        # 2. Check for Developers Section
        dev_header = page.get_by_role("heading", name="開發者專區")
        expect(dev_header).to_be_visible()

        # 3. Check for Buttons
        uml_btn = page.get_by_role("link", name="UML 架構圖")
        expect(uml_btn).to_be_visible()

        contrib_btn = page.get_by_role("link", name="貢獻指南")
        expect(contrib_btn).to_be_visible()

        legal_btn = page.get_by_role("link", name="法律聲明")
        expect(legal_btn).to_be_visible()

        # 4. Take Screenshot
        # Scroll to the section
        dev_header.scroll_into_view_if_needed()
        page.screenshot(path="verification/about_dev_section.png")
        print("Captured about_dev_section.png")

        # 5. Verify Links work
        # Check Contributing
        contrib_btn.click()
        page.wait_for_url("**/docs/CONTRIBUTING.html")
        expect(page).to_have_title("FlexiTools - 貢獻指南")
        print("Contributing page verified.")
        page.go_back()

        # Check Legal
        page.get_by_role("link", name="法律聲明").click()
        page.wait_for_url("**/docs/LEGAL.html")
        expect(page).to_have_title("FlexiTools - 法律聲明")
        print("Legal page verified.")

        browser.close()

if __name__ == "__main__":
    test_about_page_developers_section()
