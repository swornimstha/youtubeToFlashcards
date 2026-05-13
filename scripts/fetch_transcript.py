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
    """Line-by-line parser with fuzzy deduplication for scrolling transcripts."""
    segments = []
    lines = vtt_content.splitlines()
    
    current_text = []
    current_start = None
    current_end = None
    last_added_text = "" # Tracker to prevent "scrolling" duplicates

    def to_seconds(timestr):
        try:
            timestr = timestr.strip().split()[0] 
            parts = timestr.replace(',', '.').split(':')
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            return int(parts[0]) * 60 + float(parts[1])
        except:
            return 0.0

    for line in lines:
        line = line.strip()
        if "-->" in line:
            # Process the previous segment before starting a new one
            if current_start is not None and current_text:
                full_text = " ".join(current_text).strip()
                full_text = re.sub(r'<.*?>', '', full_text) # Remove internal VTT tags
                
                # DEDUPLICATION LOGIC:
                # 1. Skip if empty
                # 2. Skip if current text is just a fragment of the last added text
                # 3. Skip if last added text is a fragment of the current text (rolling captions)
                if full_text and full_text != last_added_text and last_added_text not in full_text:
                    if not full_text.upper().startswith('NOTE '):
                        segments.append({
                            'text': full_text,
                            'start': current_start,
                            'duration': round(max(0, current_end - current_start), 3)
                        })
                        last_added_text = full_text
            
            # Parse new timestamps
            try:
                times = line.split("-->")
                current_start = to_seconds(times[0])
                current_end = to_seconds(times[1])
                current_text = []
            except:
                current_start = None
        elif line and not line.isdigit() and "WEBVTT" not in line:
            current_text.append(line)

    # Final segment push
    if current_start is not None and current_text:
        full_text = " ".join(current_text).strip()
        full_text = re.sub(r'<.*?>', '', full_text)
        if full_text and full_text != last_added_text and last_added_text not in full_text:
            segments.append({
                'text': full_text,
                'start': current_start,
                'duration': round(max(0, current_end - current_start), 3)
            })

    return segments

def json3_to_json(json3_content):
    """Converts YouTube's native JSON3 subtitle format to standard JSON."""
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
        "-f", "best",
        "--print", "title",          
        "--no-simulate",             
        "--write-auto-subs",         
        "--write-subs",              
        "--sub-langs", "en.*,en,en-US",
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

    raw_title = result.stdout.strip().split('\n')[0] if not manual_title else manual_title
    safe_title = sanitize_filename(raw_title)
    
    with open("currentTitle.json", "w", encoding="utf-8") as f:
        json.dump({"videoID": video_id, "title": safe_title}, f, indent=4)
    print(f"[+] Title: {safe_title}")

    # Search for files
    all_temp_files = list(output_dir.glob(f"{temp_prefix}*"))
    sub_files = [f for f in all_temp_files if f.suffix in ['.vtt', '.json3']]
    
    if not sub_files:
        print(f"[!] Error: No English transcript found for {video_id}")
        sys.exit(1)

    # Pick the LARGEST file found to ensure we get actual content
    sub_path = max(sub_files, key=lambda f: f.stat().st_size)
    print(f"    [~] Parsing: {sub_path.name} ({sub_path.stat().st_size / 1024:.1f} KB)")
    
    with open(sub_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if sub_path.suffix == '.vtt':
            transcript_data = vtt_to_json(content)
        elif sub_path.suffix == '.json3':
            transcript_data = json3_to_json(content)
        else:
            transcript_data = []
    
    if not transcript_data:
        print(f"[!] Error: Parsed transcript is empty. Parsing logic failed.")
        sys.exit(1)
        
    final_json_path = output_dir / f"{safe_title}_transcript.json"
    with open(final_json_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, indent=2)

    # Clean up
    for f in all_temp_files:
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
