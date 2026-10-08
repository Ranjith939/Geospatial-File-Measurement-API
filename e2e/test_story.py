"""Checks that the scroll story shows real backend results, and falls back to static scenes for reduced motion."""
from playwright.sync_api import Browser, Page, expect


def test_story_uses_real_results(page: Page, site):
    page.goto(site)
    expect(page.locator("[data-scene]")).to_have_count(10)
    assert page.evaluate("ScrollTrigger.getAll().length") == 10  # each scene has its own trigger, we don't use one big timeline
    tally = page.locator("[data-tally]")
    expect(tally).to_contain_text("198")
    expect(tally).to_contain_text("196")
    expect(page.locator("[data-scene=transform] [data-vertex-one]")).to_contain_text("E,")
    expect(page.locator("[data-scene=file]")).to_contain_text("survey.zip")


def test_story_measurement_reaches_stored_value(page: Page, site):
    page.goto(site)
    data = page.evaluate("JSON.parse(document.getElementById('story-data').textContent)")
    page.locator("#workspace").scroll_into_view_if_needed()  # scrolled past every scene, so all timelines should be finished
    page.wait_for_timeout(1200)
    expected = f"{data['survey']['area_m2'] / 10000:,.2f} ha"
    expect(page.locator("[data-area]")).to_have_text(expected)


def test_reduced_motion_shows_static_final_scenes(browser: Browser, site):
    page = browser.new_context(reduced_motion="reduce").new_page()
    page.goto(site)
    assert page.evaluate("ScrollTrigger.getAll().length") == 0
    data = page.evaluate("JSON.parse(document.getElementById('story-data').textContent)")
    expect(page.locator("[data-area]")).to_have_text(f"{data['survey']['area_m2'] / 10000:,.2f} ha")


def test_api_docs_try_request(page: Page, site):
    page.goto(site)  # this is what processes the samples
    file_id = page.evaluate("JSON.parse(document.getElementById('story-data').textContent).survey.file_id")
    page.goto(f"{site}/api-docs/")
    box = page.locator("[data-try]").nth(1)
    box.locator("[data-try-id]").fill(str(file_id))
    box.locator("[data-try-send]").click()
    expect(box.locator("[data-try-out]")).to_contain_text('"filename"')


def test_no_horizontal_scroll_on_mobile(browser: Browser, site):
    page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
    page.goto(site)
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
