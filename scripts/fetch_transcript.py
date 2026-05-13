#!/usr/bin/env python3
import argparse
from pathlib import Path
import json
import sys
import subprocess
import re

def sanitize_filename(name: str) -> str:
    """Remove illegal filename characters and collapse spaces into underscores."""
    name = re.sub(r'[\\/:*?"<>|]+', "", name)
    name = re.sub(r"\s+", "_", name)
    return name

def vtt_to_json(vtt_content):
    """Converts VTT format to standard JSON format (text, start, duration)."""
    segments = []
    pattern = re.compile(r'(\d{2}:\d{2}:\d{2}.\d{3}) --> (\d{2}:\d{2}:\d{2}.\d{3})\n(.*?)(?=\n\n|\n\d|\Z)', re.DOTALL)
    
    def to_seconds(timestr):
        h, m, s = timestr.split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)

    for match in pattern.finditer(vtt_content):
        start = to_seconds(match.group(1))
        end = to_seconds(match.group(2))
        text = match.group(3).replace('\n', ' ').strip()
        text = re.sub(r'<.*?>', '', text) 
        if text:
            segments.append({
                'text': text,
                'start': start,
                'duration': round(end - start, 3)
            })
    return segments

def json3_to_json(json3_content):
    """Fallback parser: Converts YouTube's native JSON3 subtitle format to standard JSON."""
    data = json.loads(json3_content)
    segments = []
    for event in data.get('events', []):
        if 'segs' not in event:
            continue
        start = event.get('tStartMs', 0) / 1000.0
        duration = event.get('dDurationMs', 0) / 1000.0
        text = "".join([seg.get('utf8', '') for seg in event.get('segs', [])]).replace('\n', ' ').strip()
        if text:
            segments.append({
                'text': text,
                'start': round(start, 3),
                'duration': round(duration, 3)
            })
    return segments

def process_video(video_id, output_dir, cookies_path=None, manual_title=None):
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    temp_prefix = f"tmp_{video_id}"
    temp_path_template = str(output_dir / f"{temp_prefix}.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "--ignore-config",           
        "--no-playlist",             
        "--skip-download",           
        "-f", "best",                # Safe format to prevent multiplex/audio-only errors     
        "--print", "title",          
        "--no-simulate",             # CRITICAL FIX: Forces disk writes despite --print
        "--write-subs",              
        "--write-auto-subs",         
        "--sub-langs", "en,en-US,en-GB,en-CA,en-AU",
        "--sub-format", "vtt/json3/best",             
        "--convert-subs", "vtt",     
        "--quiet",
        "--no-warnings",
        "-o", temp_path_template
    ]

    if cookies_path:
        cookies_file = Path(cookies_path).expanduser()
        if cookies_file.exists():
            cmd += ["--cookies", str(cookies_file)]
    
    cmd.append(video_url)

    print(f"[+] Fetching metadata and English transcript for {video_id}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[!] yt-dlp failed: {result.stderr}")
        sys.exit(1)

    # 1. Resolve Title
    raw_title = result.stdout.strip().split('\n')[0] if not manual_title else manual_title
    safe_title = sanitize_filename(raw_title)
    
    with open("currentTitle.json", "w", encoding="utf-8") as f:
        json.dump({"videoID": video_id, "title": safe_title}, f, indent=4)
    print(f"[+] Title: {safe_title}")

    # 2. Convert Transcript (Search for both VTT and JSON3)
    sub_files = list(output_dir.glob(f"{temp_prefix}*.vtt")) + list(output_dir.glob(f"{temp_prefix}*.json3"))
    
    if not sub_files:
        all_temp_files = list(output_dir.glob(f"{temp_prefix}*"))
        print(f"[!] Error: No English transcript found for {video_id}")
        if all_temp_files:
            print(f"[!] Note: Found these files instead: {[f.name for f in all_temp_files]}")
        else:
            print(f"[!] Note: yt-dlp did not download any subtitle files. They might be disabled or blocked.")
        sys.exit(1)

    sub_path = sub_files[0]
    with open(sub_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if sub_path.suffix == '.vtt':
            transcript_data = vtt_to_json(content)
        elif sub_path.suffix == '.json3':
            transcript_data = json3_to_json(content)
        else:
            transcript_data = []
    
    final_json_path = output_dir / f"{safe_title}_transcript.json"
    with open(final_json_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, indent=2)

    # Clean up all temp files
    for f in output_dir.glob(f"{temp_prefix}*"):
        f.unlink()
    
    print(f"[+] Success! Transcript saved to: {final_json_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video_id")
    parser.add_argument("--output_dir", default="transcripts")
    parser.add_argument("--cookies", help="Path to cookies file")
    parser.add_argument("--title", help="Manual title override")
    parser.add_argument("--title_json") 
    
    args = parser.parse_args()
    process_video(args.video_id, Path(args.output_dir), args.cookies, args.title)

if __name__ == "__main__":
    main()
    
