"""Check the configured NVIDIA key against one model without displaying credentials."""
import argparse
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

parser = argparse.ArgumentParser()
parser.add_argument("--model", required=True)
args = parser.parse_args()
config = dotenv_values(Path(__file__).resolve().parents[1] / "backend/.env")
start = time.monotonic()
response = requests.post(
    "https://integrate.api.nvidia.com/v1/chat/completions",
    headers={"Authorization": "Bearer " + config["NVIDIA_API_KEY"]},
    json={"model": args.model, "messages": [
        {"role": "system", "content": "Return only valid JSON."},
        {"role": "user", "content": "Return a JSON object with status ready."}],
        "max_tokens": 256, "chat_template_kwargs": {"enable_thinking": False}},
    timeout=40,
)
print("Model:", args.model, "HTTP:", response.status_code, "Seconds:", round(time.monotonic() - start, 1))
if response.ok:
    print("Reply:", response.json()["choices"][0]["message"].get("content", "")[:200])
else:
    print("Inference request rejected. Check model availability and account access.")
raise SystemExit(0 if response.ok else 1)
