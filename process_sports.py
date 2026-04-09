#!/usr/bin/env python3
"""
AdwaSport Sports Playlist Processor - Strict Sports Filter
Filters, deduplicates, and validates ONLY genuine sports channels.
"""

import requests
import re
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import OrderedDict
from typing import List, Tuple, Optional, Dict

# ============================================
# CONFIGURATION
# ============================================

# STRICT SPORTS KEYWORDS - only real sports networks
SPORTS_KEYWORDS = [
    # Football / Soccer
    "premier league", "la liga", "serie a", "bundesliga", "ligue 1",
    "champions league", "europa league", "uefa", "concacaf", "copa libertadores",
    "mls", "sky sports", "bt sport", "bein sports", "espn", "fox sports",
    "nbc sports", "cbs sports", "dazn", "sport tv", "super sport",
    # American Sports
    "nfl network", "nba tv", "mlb network", "nhl network",
    "nfl", "nba", "mlb", "nhl", "ncaa",
    # Motorsports
    "formula 1", "f1", "motogp", "nascar", "indycar", "motor racing",
    # Combat Sports
    "ufc", "wwe", "boxing", "glory kickboxing", "one championship",
    # Cricket
    "cricket", "icc", "bcci", "willow", "star sports", "sony ten", "ptv sports",
    # Tennis / Golf
    "tennis channel", "golf channel", "golfpass", "atp", "wta",
    # Other Sports
    "rugby", "olympics", "extreme sports", "red bull tv", "fishing", "hunting",
    # Spanish / International
    "tyc sports", "espn deportes", "movistar", "gol tv", "sportitalia",
    "sportdigital", "eurosport"
]

# Channels to ALWAYS include even if name doesn't match exactly
ALWAYS_INCLUDE = [
    "bein sports", "sky sports", "bt sport", "espn", "fox sports",
    "nbc sports", "cbs sports", "dazn", "eurosport", "sport tv"
]

# Channels to EXCLUDE (false positives)
EXCLUDE_KEYWORDS = [
    "mtv", "pluto tv", "nick", "disney", "cartoon", "kids", "cooking",
    "food", "travel", "music", "comedy", "drama", "reality", "news",
    "bloomberg", "cnbc", "cnn", "fox news", "msnbc", "bbc", "weather",
    "shopping", "religion", "christian", "islam", "quran", "church"
]

INPUT_FILES = [
    "combined-playlist.m3u",
    "BD.m3u",
    "Pixelsports.m3u",
    "TVPass.m3u",
    "CricHD.m3u",
    "SportsWebcast.m3u",
    "hilaytv.m3u",
    "Moveonjoy.m3u",
    "SOFAST.m3u",
    "UDPTV.m3u",
    "Wnslive.m3u",
    "Yupptv.m3u"
]

OUTPUT_FILE = "adwa_sports.m3u"
VALIDATE_STREAMS = True          # Set to False for fast testing
MAX_VALIDATION_WORKERS = 30
VALIDATION_TIMEOUT = 5
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ============================================
# CORE LOGIC
# ============================================

def is_sports_channel(name: str) -> bool:
    """Strict check for genuine sports channels."""
    name_lower = name.lower()
    
    # First, exclude obvious non-sports
    if any(ex in name_lower for ex in EXCLUDE_KEYWORDS):
        return False
    
    # Then check for sports keywords
    if any(kw in name_lower for kw in SPORTS_KEYWORDS):
        return True
    
    # Always include list (case-insensitive partial match)
    if any(inc in name_lower for inc in ALWAYS_INCLUDE):
        return True
    
    return False

def parse_m3u(file_path: str) -> List[Tuple[str, str, Dict]]:
    channels = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF'):
            extinf = line
            vlcopts = []
            i += 1
            while i < len(lines) and lines[i].startswith('#EXTVLCOPT'):
                vlcopts.append(lines[i].strip())
                i += 1
            if i < len(lines) and not lines[i].startswith('#'):
                url = lines[i].strip()
                meta = {
                    'vlcopts': vlcopts,
                    'tvg_id': re.search(r'tvg-id="([^"]+)"', extinf),
                    'tvg_logo': re.search(r'tvg-logo="([^"]+)"', extinf),
                    'group': re.search(r'group-title="([^"]+)"', extinf)
                }
                channels.append((extinf, url, meta))
            i += 1
        else:
            i += 1
    return channels

def validate_stream(url: str) -> bool:
    try:
        resp = requests.get(url, headers={'User-Agent': USER_AGENT}, stream=True, timeout=VALIDATION_TIMEOUT)
        if resp.status_code == 200:
            chunk = next(resp.iter_content(512), b'')
            return b'#EXTM3U' in chunk or b'<?xml' in chunk
        return False
    except:
        return False

def main():
    print("🚀 AdwaSport Strict Sports Processor")
    all_channels = OrderedDict()
    seen_urls = set()
    
    for f in INPUT_FILES:
        print(f"📂 {f}...")
        for extinf, url, meta in parse_m3u(f):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            name_match = re.search(r',([^,]+)$', extinf)
            if not name_match:
                continue
            name = name_match.group(1).strip()
            if not is_sports_channel(name):
                continue
            key = meta['tvg_id'].group(1) if meta['tvg_id'] else name.lower()
            if key not in all_channels:
                all_channels[key] = (extinf, url, meta, name)
    
    print(f"\n🎯 Found {len(all_channels)} unique sports channels.")
    
    if VALIDATE_STREAMS:
        print(f"🔍 Validating with {MAX_VALIDATION_WORKERS} workers...")
        valid = OrderedDict()
        with ThreadPoolExecutor(max_workers=MAX_VALIDATION_WORKERS) as ex:
            futures = {ex.submit(validate_stream, data[1]): key for key, data in all_channels.items()}
            for i, f in enumerate(as_completed(futures), 1):
                key = futures[f]
                extinf, url, meta, name = all_channels[key]
                if f.result():
                    valid[key] = all_channels[key]
                    print(f"   [{i}/{len(all_channels)}] ✅ {name}")
                else:
                    print(f"   [{i}/{len(all_channels)}] ❌ {name}")
        all_channels = valid
        print(f"\n🏆 Alive streams: {len(all_channels)}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for extinf, url, meta, name in all_channels.values():
            f.write(f"{extinf}\n")
            for opt in meta['vlcopts']:
                f.write(f"{opt}\n")
            f.write(f"{url}\n")
    print(f"💾 Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()