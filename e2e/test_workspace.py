"""Upload → recorded stages → results → selection → technical mode → 2.5D, in a real browser."""
import re

from playwright.sync_api import Page, expect


def upload(page: Page, site: str, path: str):
    page.goto(f"{site}/#workspace")
    page.set_input_files("#workspace [data-input]", path)


def test_upload_shows_recorded_stages_then_results(page: Page, site, sample):
    upload(page, site, sample("land_parcels.zip"))
    expect(page.locator(".pipeline")).to_be_visible()
    expect(page.locator(".pipeline li", has_text="Selecting measurement CRS")).to_be_visible()
    expect(page.locator("tbody tr")).to_have_count(100)  # first page of 198
    expect(page.locator(".notice")).to_contain_text("2 of 198 features could not be measured")
    expect(page.locator(".crs")).to_contain_text("EPSG:32643")


def test_select_feature_shows_real_measurement(page: Page, site, sample):
    upload(page, site, sample("polygon.kml"))
    page.locator("tbody tr").first.click()
    expect(page.locator(".measure__sub")).to_have_text(re.compile(r"1,000,000\.\d\d m²"))
    expect(page.locator(".map .overlay text", has_text="100.00 ha")).to_have_count(1)
    page.get_by_role("button", name="Technical").click()
    expect(page.locator(".tech")).to_contain_text("Geodesic check")


def test_failed_feature_is_explained(page: Page, site, sample):
    upload(page, site, sample("land_parcels.zip"))
    page.get_by_role("button", name="View feature #83").click()
    expect(page.locator(".ws-side [role=alert]")).to_contain_text("Self-intersection")
    expect(page.locator(".ws-side [role=alert]")).to_contain_text("196 other features were processed successfully")


def test_table_is_keyboard_usable(page: Page, site, sample):
    upload(page, site, sample("mixed_geometry.kml"))
    row = page.locator("tbody tr").nth(2)
    row.focus()
    page.keyboard.press("Enter")
    expect(row).to_have_attribute("aria-selected", "true")
    expect(page.locator(".measure__big")).to_have_text(re.compile(r"1\.00 km"))


def test_invalid_upload_shows_real_error(page: Page, site, sample):
    upload(page, site, sample("invalid_shapefile.zip"))
    alert = page.locator("#workspace [role=alert]")
    expect(alert).to_contain_text("does not contain a valid Shapefile structure")
    expect(alert).to_contain_text(".shx")


def test_missing_crs_state(page: Page, site, sample):
    upload(page, site, sample("missing_crs.zip"))
    expect(page.locator(".ws-side [role=alert]")).to_contain_text("CRS information unavailable")
    expect(page.locator(".map-note")).to_contain_text("CRS unknown")


def test_inspector_lazy_loads_three(page: Page, site, sample):
    upload(page, site, sample("survey.zip"))
    expect(page.locator("tbody tr")).to_have_count(1)
    three = []
    page.on("request", lambda r: "three.module" in r.url and three.append(r.url))
    assert not three  # not part of the normal page load
    page.get_by_role("button", name="Inspect 2.5D").click()
    expect(page.locator(".inspector canvas, .viz__fallback").first).to_be_visible()
    expect(page.locator(".inspector__note, .viz__fallback").first).to_be_visible()
