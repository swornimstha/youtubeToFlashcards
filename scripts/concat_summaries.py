#!/usr/bin/env python3
"""
concat_summaries.py
-----------------------------
Concatenates all full_summary.txt files within a target directory.
Accepts a direct path to the folder.
"""

import argparse
from pathlib import Path

def concat_playlist_summaries(target_dir: Path):
    # Ensure the path exists
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"[!] Target directory not found or is not a directory: {target_dir}")
        return

    # Find all subdirectories
    video_dirs = sorted([d for d in target_dir.iterdir() if d.is_dir()])
    
    if not video_dirs:
        print(f"[!] No video subdirectories found in {target_dir}")
        return

    content_blocks = []

    for v_dir in video_dirs:
        summary_file = v_dir / "full_summary.txt"
        
        if summary_file.exists():
            video_title = v_dir.name
            print(f"[+] Adding: {video_title}")
            
            with open(summary_file, "r", encoding="utf-8") as f:
                text = f.read().strip()
            
            # Create a header marker
            marker = f"\n{'='*60}\nVIDEO: {video_title}\n{'='*60}\n"
            content_blocks.append(marker + text)
        else:
            # Skip if there's no summary file in this specific subfolder
            continue

    if content_blocks:
        # Save the master file inside the target directory
        output_filename = f"MASTER_SUMMARY_{target_dir.name}.md"
        output_path = target_dir / output_filename
        
        with open(output_path, "w", encoding="utf-8") as out:
            out.write("\n\n".join(content_blocks))
        
        print(f"\n[DONE] Combined summary saved to: {output_path}")
    else:
        print("[!] No 'full_summary.txt' files found in subdirectories.")

def main():
    parser = argparse.ArgumentParser(description="Concatenate summaries by providing a folder path.")
    parser.add_argument("path", help="Path to the playlist folder (e.g., summaries/My_Playlist)")
    args = parser.parse_args()

    # Resolve the path to handle absolute or relative inputs
    target_path = Path(args.path).resolve()
    concat_playlist_summaries(target_path)

if __name__ == "__main__":
    main()
