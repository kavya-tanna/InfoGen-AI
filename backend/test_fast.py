import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("NVIDIA_API_KEY", "")
if not api_key:
    print("NVIDIA_API_KEY not configured in environment or .env.")
    exit(0)

url = 'https://integrate.api.nvidia.com/v1/chat/completions'
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}
payload = {
    'model': 'meta/llama-3.2-11b-vision-instruct',
    'messages': [
        {'role': 'system', 'content': 'You are a video scriptwriter. Return valid JSON: {"title":"...","script":"...","scenes":[{"scene":1,"visual":"...","narration":"..."}]}'},
        {'role': 'user', 'content': 'Create a short 3-scene video package about database normalization.'}
    ],
    'max_tokens': 1200,
    'temperature': 0.2
}
t0 = time.time()
r = requests.post(url, headers=headers, json=payload, timeout=25)
print('Status:', r.status_code, 'Time:', round(time.time()-t0, 2), 's')
print('Content:', r.json()['choices'][0]['message']['content'][:200])
