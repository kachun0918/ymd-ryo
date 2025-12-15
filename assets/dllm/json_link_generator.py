import os
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
GITHUB_BASE = "https://raw.githubusercontent.com/kachun0918/ymd-ryo/main/assets/dllm/"
files = []

print(f"📂 Scanning directory: {script_dir}")


for filename in os.listdir(script_dir):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        full_url = f"{GITHUB_BASE}{filename}"
        files.append(full_url)

output_path = os.path.join(script_dir, "dllm_links.json")

with open(output_path, "w") as f:
    json.dump(files, f, indent=4)

print(f"✅ Generated dllm_links.json at: {output_path}")
print(f"🎉 Found {len(files)} links!")