"""Extractive deliverables for offline use and provider failure recovery."""
import re

from app.schemas.outputs import OUTPUT_FORMAT_MAP
from app.services.validator import _extract_indicators

UNAVAILABLE = "Not available in source."


def build_grounded(format_name, ci, audience="General Public", detail="Standard", warning=""):
    facts = [f["claim"] for f in ci.facts][:4 if detail == "Concise" else 8]
    facts = facts or [ci.source_text or UNAVAILABLE]
    actions = ci.recommendations or [UNAVAILABLE]
    risks = ci.risks or [UNAVAILABLE]
    title = ci.title or facts[0][:120]
    summary = " ".join(facts[:2])
    severity_match = re.search(r"severity\s*:\s*(critical|high|medium|low|informational)\b", ci.source_text, re.I)
    severity = severity_match.group(1).upper() if severity_match else "UNSPECIFIED"
    groups = [("Overview", facts[:2]), ("Key Findings", facts[2:5] or facts[:2]),
              ("Reported Impact and Limitations", risks), ("Source Recommendations", actions),
              ("Missing Information", [UNAVAILABLE, ci.uncertainties[0]])]
    data = {}
    if format_name == "Executive Summary":
        data = dict(headline=title, key_takeaways=facts[:4], context=summary,
                    major_findings=facts, business_impact=" ".join(risks), risks=risks,
                    decisions_required=[UNAVAILABLE], priority=severity,
                    recommended_actions=[dict(action=a, priority="UNSPECIFIED", timeline=UNAVAILABLE) for a in actions],
                    conclusion=ci.uncertainties[0])
    elif format_name == "Advisory Document":
        affected = [f["claim"] for f in ci.facts if re.search(r"\baffected\b", f["claim"], re.I)]
        data = dict(title=title, severity=severity, executive_overview=summary,
                    affected_systems=affected or [UNAVAILABLE], threat_description=" ".join(risks),
                    indicators=sorted(_extract_indicators(ci.source_text)), impact=" ".join(risks),
                    technical_analysis=" ".join(facts), risk_assessment=" ".join(risks),
                    immediate_actions=actions, mitigation=actions,
                    long_term_recommendations=[UNAVAILABLE], confidence_level="SOURCE ONLY")
    elif format_name == "LinkedIn Post":
        data = dict(hook=title, post=summary, key_insights=facts[:5],
                    cta="Source recommendations: " + actions[0], hashtags=[],
                    carousel_slides=[dict(slide_number=i, headline=h, body=" ".join(p))
                                     for i, (h, p) in enumerate(groups, 1)])
    elif format_name == "Twitter / X Post":
        def short(s, n=270):
            return s if len(s) <= n else s[:n-3].rsplit(" ", 1)[0] + "..."
        data = dict(primary_post=short(facts[0]), thread=[short(f"{i}/ {p}") for i, p in enumerate(facts, 1)],
                    key_indicators=sorted(_extract_indicators(ci.source_text)), hashtags=[])
    elif format_name == "Infographic":
        data = dict(title=title, subtitle=ci.content_type, key_messages=facts[:4],
                    key_statistics=[dict(value=n["value"], label=n["context"], source_reference="Supplied source") for n in ci.numbers],
                    sections=[dict(section_title=h, content=" ".join(p), visual_element="text") for h, p in groups],
                    layout="Vertical briefing", information_hierarchy=[h for h, _ in groups],
                    color_recommendations=dict(primary="#26354a", secondary="#48755b", accent="#ad4263"))
    elif format_name == "Presentation Deck":
        data = dict(title=title, slides=[
            dict(slide_number=i, title=h, category=ci.content_type.upper(), purpose=h,
                 key_points=p[:4], body_content="", takeaway="",
                 speaker_notes="Source excerpts: " + " ".join(p), visual_recommendation="Source excerpts")
            for i, (h, p) in enumerate(groups, 1)])
    elif format_name == "Video Package":
        scenes = []
        cursor = 0
        cues = ["WEBVTT\n"]
        for i, (heading, passages) in enumerate(groups[:4], 1):
            narration = " ".join(passages[:2])
            duration = max(12, round(len(narration.split()) / 2.3))
            end = cursor + duration
            start_label, end_label = f"{cursor//60:02}:{cursor%60:02}", f"{end//60:02}:{end%60:02}"
            scenes.append(dict(scene_number=i, start_time=start_label, end_time=end_label,
                               title=heading, narration=narration, visual="Source excerpt with heading",
                               camera="Static", on_screen_text=passages[0][:150]))
            cues.append(f"{i}\n00:{start_label}.000 --> 00:{end_label}.000\n{narration}\n")
            cursor = end
        data = dict(title=title, target_audience=audience, objective="Brief the audience on the supplied source",
                    duration_seconds=cursor, scenes=scenes, script="\n\n".join(s["narration"] for s in scenes),
                    vtt="\n".join(cues), production_notes="Extractive storyboard; browser narration is optional.")
    return OUTPUT_FORMAT_MAP[format_name](
        **data, generation_mode="extractive",
        warnings=[warning or "Offline extractive mode: source wording is preserved; translation and tone rewriting are unavailable."],
    )
