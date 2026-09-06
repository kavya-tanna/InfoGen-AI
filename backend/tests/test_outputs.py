"""Tests for output schema validation."""
import pytest
from app.schemas.outputs import (
    VideoPackageOutput, LinkedInPostOutput, TwitterPostOutput,
    AdvisoryDocumentOutput, InfographicOutput, ExecutiveSummaryOutput,
    PresentationDeckOutput, OUTPUT_FORMAT_MAP, OUTPUT_KEY_MAP
)
from app.services.validator import validate_output, check_grounding


def test_video_package_schema():
    data = {"type": "video_package", "title": "Test", "script": "Test script", "scenes": [], "duration_seconds": 60}
    model = VideoPackageOutput(**data)
    assert model.title == "Test"
    assert model.duration_seconds == 60

def test_linkedin_post_schema():
    data = {"type": "linkedin_post", "hook": "Hook!", "post": "Body", "hashtags": ["#test"]}
    model = LinkedInPostOutput(**data)
    assert model.hook == "Hook!"
    assert "#test" in model.hashtags

def test_twitter_post_schema():
    data = {"type": "twitter_post", "primary_post": "Tweet", "thread": ["1", "2"], "hashtags": ["#x"]}
    model = TwitterPostOutput(**data)
    assert model.primary_post == "Tweet"
    assert len(model.thread) == 2

def test_advisory_document_schema():
    data = {"type": "advisory_document", "title": "Advisory", "severity": "HIGH", "indicators": ["CVE-2024-1234"]}
    model = AdvisoryDocumentOutput(**data)
    assert model.severity == "HIGH"
    assert "CVE-2024-1234" in model.indicators

def test_infographic_schema():
    data = {"type": "infographic", "title": "Infographic", "subtitle": "Sub"}
    model = InfographicOutput(**data)
    assert model.title == "Infographic"

def test_executive_summary_schema():
    data = {"type": "executive_summary", "headline": "Headline", "key_takeaways": ["a", "b", "c"]}
    model = ExecutiveSummaryOutput(**data)
    assert len(model.key_takeaways) == 3

def test_presentation_deck_schema():
    data = {"type": "presentation_deck", "title": "Deck", "slides": [{"slide_number": 1, "title": "Intro"}]}
    model = PresentationDeckOutput(**data)
    assert len(model.slides) == 1

def test_output_format_map_has_all_seven():
    assert len(OUTPUT_FORMAT_MAP) == 7
    assert "Video Package" in OUTPUT_FORMAT_MAP
    assert "LinkedIn Post" in OUTPUT_FORMAT_MAP
    assert "Twitter / X Post" in OUTPUT_FORMAT_MAP
    assert "Advisory Document" in OUTPUT_FORMAT_MAP
    assert "Infographic" in OUTPUT_FORMAT_MAP
    assert "Executive Summary" in OUTPUT_FORMAT_MAP
    assert "Presentation Deck" in OUTPUT_FORMAT_MAP

def test_output_key_map_has_all_seven():
    assert len(OUTPUT_KEY_MAP) == 7

def test_grounding_check_clean():
    source = "CVE-2024-12345 affects 192.168.1.1"
    generated = "The vulnerability CVE-2024-12345 impacts server 192.168.1.1"
    result = check_grounding(source, generated)
    assert result["score"] == 100.0
    assert result["status"] == "clean"
    assert len(result["hallucinated_indicators"]) == 0

def test_grounding_check_hallucination():
    source = "CVE-2024-12345 is critical"
    generated = "CVE-2024-12345 and CVE-2024-99999 are critical"
    result = check_grounding(source, generated)
    assert "CVE-2024-99999" in result["hallucinated_indicators"]
    assert result["status"] == "warning"

def test_grounding_no_iocs():
    source = "General article about cloud computing."
    generated = "Cloud computing is transforming business."
    result = check_grounding(source, generated)
    assert result["score"] == 100.0

def test_validate_output_valid():
    data = {"type": "executive_summary", "headline": "Test", "key_takeaways": ["a"]}
    model, warnings = validate_output(data, ExecutiveSummaryOutput)
    assert model.headline == "Test"

def test_validate_output_defaults():
    model = ExecutiveSummaryOutput()
    assert model.type == "executive_summary"
    assert model.headline == ""
