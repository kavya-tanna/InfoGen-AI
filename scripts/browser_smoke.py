"""Optional browser check: pip install playwright; python scripts/browser_smoke.py."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8000")
parser.add_argument("--channel", default="msedge")
parser.add_argument("--replay", action="store_true", help="Replay saved live API results for visual regression, without new provider calls")
parser.add_argument("--live", action="store_true", help="Require live AI outputs; sends sample text to the configured provider")
parser.add_argument("--sample", default="all", choices=["all", "news", "advisory", "report", "incident"])
args = parser.parse_args()
artifacts = Path(__file__).resolve().parents[1] / "test-artifacts"
if args.live or args.replay:
    artifacts = artifacts / "live-browser"
artifacts.mkdir(parents=True, exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=args.channel, headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    if args.replay:
        def replay(route):
            body = route.request.post_data_json
            source = body.get("source", "")
            name = "news" if "Riverton" in source else "advisory" if "Northstar" in source else "report" if "240" in source else "incident"
            result_path = Path(__file__).resolve().parents[1] / "test-artifacts" / f"live-{name}-English.json"
            route.fulfill(status=200, content_type="application/json", body=result_path.read_text(encoding="utf-8"))
        page.route("**/api/generate", replay)
    page.goto(args.url, wait_until="networkidle")
    expect(page.locator("#samplePicker option")).to_have_count(5)
    page.locator("#generateBtn").click()
    expect(page.locator("#inputError")).to_contain_text("Please add source")
    page.screenshot(path=str(artifacts / "desktop-input.png"), full_page=True)
    for sample in ["news", "advisory", "report", "incident"]:
        if args.sample not in ("all", sample):
            continue
        page.locator("#samplePicker").select_option(sample)
        text = page.locator("#sourceText").input_value()
        with page.expect_response(lambda r: r.url.endswith("/api/generate") and r.request.method == "POST", timeout=180000) as response:
            page.locator("#generateBtn").click()
        result = response.value.json()
        if args.live:
            assert result["metadata"]["provider"] == "nvidia"
            assert all(o["generation_mode"] == "ai" for o in result["outputs"].values()), result["metadata"]["warnings"]
        expect(page.locator("#generatedStatus")).to_have_text("7 Outputs Generated", timeout=180000)
        expect(page.locator("#generateBtn")).to_be_enabled()
        expect(page.locator("#sourceText")).to_have_value(text)
        expect(page.locator("#resultNotice")).to_contain_text("AI draft" if args.live or args.replay else "Offline extractive mode")
        for key in ["video", "summary", "advisory", "linkedin", "twitter", "infographic", "presentation"]:
            page.locator(f'.output-nav button[data-output="{key}"]').click()
            expect(page.locator("#previewBody")).not_to_be_empty()
        page.locator('.output-nav button[data-output="linkedin"]').click()
        expect(page.locator('[data-publishable="linkedin"]')).to_have_text(result["outputs"]["linkedin_post"]["post"])
        assert page.evaluate("publishableText('linkedin', generatedOutputs.linkedin_post)") == result["outputs"]["linkedin_post"]["post"]
        assert "Ready for LinkedIn Publication" not in page.locator("#previewBody").inner_text()
        page.screenshot(path=str(artifacts / f"{sample}-linkedin.png"), full_page=True)
        page.locator('.output-nav button[data-output="presentation"]').click()
        expect(page.locator(".deck-slide")).to_have_count(len(result["outputs"]["presentation_deck"]["slides"]))
        page.screenshot(path=str(artifacts / f"{sample}-presentation.png"), full_page=True)
        page.locator('.output-nav button[data-output="summary"]').click()
        expect(page.locator("#previewBody")).to_contain_text(result["outputs"]["executive_summary"]["headline"])
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.screenshot(path=str(artifacts / f"{sample}-desktop.png"), full_page=True)
        print(f"PASS browser sample: {sample}", flush=True)
    # Re-generation after output selection exercises the formerly stale button counter.
    page.locator("#deselectBtn").click()
    expect(page.locator("#generateCount")).to_have_text("0")
    page.locator("#deselectBtn").click()
    expect(page.locator("#generateCount")).to_have_text("7")
    page.locator('.output-nav button[data-output="video"]').click()
    canvas_before = page.locator("#videoPlayerCanvas").evaluate("(c) => c.toDataURL()")
    assert page.locator("#videoPlayerCanvas").evaluate("(c) => new Set(c.getContext('2d').getImageData(0,0,c.width,c.height).data).size > 30")
    page.locator("#videoPlayOverlay").click()
    page.wait_for_timeout(1200)
    canvas_after = page.locator("#videoPlayerCanvas").evaluate("(c) => c.toDataURL()")
    assert canvas_before != canvas_after, "Video canvas did not update"
    page.locator('.output-nav button[data-output="summary"]').click()
    with page.expect_download() as downloaded:
        page.locator("#downloadCurrentBtn").click()
    assert downloaded.value.suggested_filename.endswith(".pdf")
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator("#samplePicker").select_option("report")
    with page.expect_response(lambda r: r.url.endswith("/api/generate") and r.request.method == "POST", timeout=180000) as response:
        page.locator("#generateBtn").click()
    if args.live:
        assert all(o["generation_mode"] == "ai" for o in response.value.json()["outputs"].values())
    expect(page.locator("#generateBtn")).to_be_enabled(timeout=180000)
    page.locator('.output-nav button[data-output="summary"]').click()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.screenshot(path=str(artifacts / "mobile-results.png"), full_page=True)
    page.locator("#sourceText").scroll_into_view_if_needed()
    page.screenshot(path=str(artifacts / "mobile-input.png"))
    # A failed request retains the source and permits another attempt.
    page.route("**/api/generate", lambda route: route.abort())
    page.locator("#generateBtn").click()
    expect(page.locator("#inputError")).to_be_visible()
    expect(page.locator("#generateBtn")).to_be_enabled()
    assert page.locator("#sourceText").input_value()
    assert not errors, errors
    print("PASS mobile layout, export download, empty input, backend failure, and browser runtime", flush=True)
    browser.close()
