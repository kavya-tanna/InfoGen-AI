"""Opt-in live NVIDIA verification. Uses server credentials, never reads or prints keys."""
import argparse
import json
import time
from pathlib import Path

import requests

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8000")
parser.add_argument("--sample", default="all")
parser.add_argument("--language", default="English")
parser.add_argument("--formats", default="Video Package,LinkedIn Post,Twitter / X Post,Advisory Document,Infographic,Executive Summary,Presentation Deck")
args = parser.parse_args()
health = requests.get(args.url + "/api/health", timeout=10).json()
assert health["provider"] == "nvidia" and not health["demo_mode"], "Start the server with NVIDIA configured."
samples = requests.get(args.url + "/api/samples", timeout=10).json()
report = []
failed = False
artifacts = Path(__file__).resolve().parents[1] / "test-artifacts"
artifacts.mkdir(exist_ok=True)
for sample in samples:
    if args.sample not in ("all", sample["id"]):
        continue
    start = time.monotonic()
    response = requests.post(args.url + "/api/generate", json={
        "source": sample["content"], "content_type": sample["content_type"],
        "language": args.language, "audience": "General Public", "tone": "Professional",
        "objective": "Inform", "detail": "Standard", "output_format": args.formats,
    }, timeout=180)
    data = response.json()
    modes = {key: value["generation_mode"] for key, value in data.get("outputs", {}).items()}
    providers = {key: value.get("provider", "") for key, value in data.get("outputs", {}).items()}
    ok = response.ok and len(modes) == len(args.formats.split(",")) and all(mode == "ai" for mode in modes.values())
    record = {"sample": sample["id"], "language": args.language, "status": response.status_code,
              "seconds": round(time.monotonic() - start, 1), "model": health["model"],
              "modes": modes, "providers": providers, "passed": ok, "warnings": data.get("metadata", {}).get("warnings", [])}
    report.append(record)
    print(json.dumps(record), flush=True)
    (artifacts / f"live-{sample['id']}-{args.language}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    failed = failed or not ok
(artifacts / "live-verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
raise SystemExit(1 if failed else 0)
