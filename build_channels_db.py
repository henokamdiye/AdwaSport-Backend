#!/usr/bin/env python3
"""
Parse adwa_sports.m3u and build a channels.json database.
"""

import json
import re
import os

M3U_FILE = "adwa_sports.m3u"
OUTPUT_FILE = "channels.json"

def parse_m3u(file_path):
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return []

    channels = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            # Extract metadata
            tvg_id = re.search(r'tvg-id="([^"]+)"', line)
            tvg_logo = re.search(r'tvg-logo="([^"]+)"', line)
            group = re.search(r'group-title="([^"]+)"', line)
            name_match = re.search(r',([^,]+)$', line)
            name = name_match.group(1).strip() if name_match else "Unknown"

            # Skip VLC options
            i += 1
            while i < len(lines) and lines[i].startswith("#EXTVLCOPT"):
                i += 1

            # URL is the next non‑comment line
            url = ""
            if i < len(lines) and not lines[i].startswith("#"):
                url = lines[i].strip()

            channels.append({
                "id": tvg_id.group(1) if tvg_id else re.sub(r'[^a-z0-9_]', '_', name.lower()),
                "name": name,
                "logo": tvg_logo.group(1) if tvg_logo else "",
                "group": group.group(1) if group else "Sports",
                "url": url
            })
        i += 1
    return channels

if __name__ == "__main__":
    channels = parse_m3u(M3U_FILE)
    if channels:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump({"channels": channels}, f, indent=2, ensure_ascii=False)
        print(f"✅ Built channels.json with {len(channels)} channels.")
    else:
        print("❌ No channels found. Make sure adwa_sports.m3u exists.")