#!/usr/bin/env python3
"""
Video Splicer - Creates multiple candidate videos from clips based on sample_output.json
Uses FFmpeg to extract and combine video segments with different strategies.
"""

import json
import subprocess
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any
import argparse
from datetime import datetime

class VideoSplicer:
    def __init__(self, input_video: str, sample_output_path: str, output_dir: str = "candidate_videos"):
        self.input_video = input_video
        self.sample_output_path = sample_output_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Load the sample output data
        with open(sample_output_path, 'r') as f:
            self.data = json.load(f)
        
        self.clips = self.data['clips']
        print(f"Loaded {len(self.clips)} clips from {sample_output_path}")
        
    def format_time(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS.mmm format for FFmpeg"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def extract_clip(self, start: float, end: float, output_path: str) -> bool:
        """Extract a single clip using FFmpeg with fallbacks.

        Try stream copy first; if it fails (e.g., non-keyframe start), fall back to re-encode.
        """
        start_time = self.format_time(start)
        duration = max(0.0, end - start)

        # Attempt 1: copy (fast) with -ss before -i for keyframe-seeking
        cmd_copy_fast = [
            'ffmpeg', '-y',
            '-ss', start_time,
            '-t', str(duration),
            '-i', self.input_video,
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            output_path
        ]
        try:
            subprocess.run(cmd_copy_fast, capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e1:
            # Attempt 2: copy with -ss after -i
            cmd_copy_slow = [
                'ffmpeg', '-y',
                '-i', self.input_video,
                '-ss', start_time,
                '-t', str(duration),
                '-c', 'copy',
                '-avoid_negative_ts', 'make_zero',
                output_path
            ]
            try:
                subprocess.run(cmd_copy_slow, capture_output=True, text=True, check=True)
                return True
            except subprocess.CalledProcessError as e2:
                # Attempt 3: re-encode
                cmd_encode = [
                    'ffmpeg', '-y',
                    '-ss', start_time,
                    '-t', str(duration),
                    '-i', self.input_video,
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                    '-c:a', 'aac', '-b:a', '128k',
                    output_path
                ]
                try:
                    subprocess.run(cmd_encode, capture_output=True, text=True, check=True)
                    return True
                except subprocess.CalledProcessError as e3:
                    print(
                        f"Error extracting clip {start}-{end}: copy1={e1.stderr}\ncopy2={e2.stderr}\nencode={e3.stderr}"
                    )
                    return False
    
    def create_concat_file(self, clip_paths: List[str], concat_file_path: str):
        """Create a concat file for FFmpeg"""
        with open(concat_file_path, 'w') as f:
            for path in clip_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")
    
    def concatenate_videos(self, clip_paths: List[str], output_path: str, encode: bool = True) -> bool:
        """Concatenate multiple video clips.

        By default re-encodes to ensure consistent playback in browsers (prevents
        early stop issues and index problems). Set encode=False to try stream copy.
        """
        concat_file = self.output_dir / "concat_list.txt"
        self.create_concat_file(clip_paths, str(concat_file))
        if encode:
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat', '-safe', '0',
                '-i', str(concat_file),
                '-fflags', '+genpts', '-vsync', '2',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                '-c:a', 'aac', '-b:a', '128k',
                str(output_path)
            ]
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                return True
            except subprocess.CalledProcessError as e:
                print(f"Error concatenating videos (encode): {e.stderr}")
                return False
        else:
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                '-y',
                str(output_path)
            ]
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                return True
            except subprocess.CalledProcessError as e:
                print(f"Error concatenating videos (copy): {e.stderr}")
                return False
    
    def create_candidate_1_top_clips(self):
        """Candidate 1: All top-ranked clips in order"""
        print("Creating Candidate 1: All top clips in order...")
        
        clip_paths = []
        for i, clip in enumerate(self.clips):
            clip_path = self.output_dir / f"clip_{i+1}_{clip['rank']}.mp4"
            if self.extract_clip(clip['start'], clip['end'], str(clip_path)):
                clip_paths.append(str(clip_path))
        
        if clip_paths:
            output_path = self.output_dir / "candidate_1_all_clips.mp4"
            if self.concatenate_videos(clip_paths, str(output_path), encode=True):
                print(f"✓ Created: {output_path}")
                return str(output_path)
        return None
    
    def create_candidate_2_high_score(self):
        """Candidate 2: Only clips with score > 0.85"""
        print("Creating Candidate 2: High score clips only...")
        
        high_score_clips = [clip for clip in self.clips if clip['score'] > 0.85]
        clip_paths = []
        
        for i, clip in enumerate(high_score_clips):
            clip_path = self.output_dir / f"high_score_clip_{i+1}.mp4"
            if self.extract_clip(clip['start'], clip['end'], str(clip_path)):
                clip_paths.append(str(clip_path))
        
        if clip_paths:
            output_path = self.output_dir / "candidate_2_high_score.mp4"
            if self.concatenate_videos(clip_paths, str(output_path), encode=True):
                print(f"✓ Created: {output_path}")
                return str(output_path)
        return None
    
    def create_candidate_3_short_clips(self):
        """Candidate 3: Clips under 35 seconds for quick consumption"""
        print("Creating Candidate 3: Short clips only...")
        
        short_clips = [clip for clip in self.clips if clip['duration'] < 35]
        clip_paths = []
        
        for i, clip in enumerate(short_clips):
            clip_path = self.output_dir / f"short_clip_{i+1}.mp4"
            if self.extract_clip(clip['start'], clip['end'], str(clip_path)):
                clip_paths.append(str(clip_path))
        
        if clip_paths:
            output_path = self.output_dir / "candidate_3_short_clips.mp4"
            if self.concatenate_videos(clip_paths, str(output_path), encode=True):
                print(f"✓ Created: {output_path}")
                return str(output_path)
        return None
    
    def create_candidate_4_best_hooks(self):
        """Candidate 4: Clips with the best hook types"""
        print("Creating Candidate 4: Best hook clips...")
        
        # Prioritize clips with certain hook types
        hook_priority = ["definition/intro", "personal journey", "future goals", "list/enumeration"]
        best_hooks = []
        
        for clip in self.clips:
            hooks = clip['reasons'].get('hook', [])
            if any(hook in hooks for hook in hook_priority):
                best_hooks.append(clip)
        
        # Sort by score
        best_hooks.sort(key=lambda x: x['score'], reverse=True)
        
        clip_paths = []
        for i, clip in enumerate(best_hooks):
            clip_path = self.output_dir / f"hook_clip_{i+1}.mp4"
            if self.extract_clip(clip['start'], clip['end'], str(clip_path)):
                clip_paths.append(str(clip_path))
        
        if clip_paths:
            output_path = self.output_dir / "candidate_4_best_hooks.mp4"
            if self.concatenate_videos(clip_paths, str(output_path), encode=True):
                print(f"✓ Created: {output_path}")
                return str(output_path)
        return None
    
    def create_candidate_5_chronological(self):
        """Candidate 5: Clips in chronological order (by start time)"""
        print("Creating Candidate 5: Chronological order...")
        
        # Sort clips by start time
        chronological_clips = sorted(self.clips, key=lambda x: x['start'])
        clip_paths = []
        
        for i, clip in enumerate(chronological_clips):
            clip_path = self.output_dir / f"chrono_clip_{i+1}.mp4"
            if self.extract_clip(clip['start'], clip['end'], str(clip_path)):
                clip_paths.append(str(clip_path))
        
        if clip_paths:
            output_path = self.output_dir / "candidate_5_chronological.mp4"
            if self.concatenate_videos(clip_paths, str(output_path), encode=True):
                print(f"✓ Created: {output_path}")
                return str(output_path)
        return None
    
    def create_candidate_6_trimmed_segments(self):
        """Candidate 6: Use individual segments instead of full clips"""
        print("Creating Candidate 6: Individual segments...")
        
        all_segments = []
        for clip in self.clips:
            for segment in clip['segments']:
                all_segments.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment['text'],
                    'clip_rank': clip['rank']
                })
        
        # Sort by clip rank, then by start time
        all_segments.sort(key=lambda x: (x['clip_rank'], x['start']))
        
        clip_paths = []
        for i, segment in enumerate(all_segments[:10]):  # Limit to first 10 segments
            clip_path = self.output_dir / f"segment_{i+1}.mp4"
            if self.extract_clip(segment['start'], segment['end'], str(clip_path)):
                clip_paths.append(str(clip_path))
        
        if clip_paths:
            output_path = self.output_dir / "candidate_6_segments.mp4"
            if self.concatenate_videos(clip_paths, str(output_path), encode=True):
                print(f"✓ Created: {output_path}")
                return str(output_path)
        return None
    
    def create_candidate_7_no_promo(self):
        """Candidate 7: Clips without promotional content"""
        print("Creating Candidate 7: No promotional content...")
        
        no_promo_clips = [clip for clip in self.clips if "promo" not in clip['reasons'].get('penalties', [])]
        clip_paths = []
        
        for i, clip in enumerate(no_promo_clips):
            clip_path = self.output_dir / f"no_promo_clip_{i+1}.mp4"
            if self.extract_clip(clip['start'], clip['end'], str(clip_path)):
                clip_paths.append(str(clip_path))
        
        if clip_paths:
            output_path = self.output_dir / "candidate_7_no_promo.mp4"
            if self.concatenate_videos(clip_paths, str(output_path), encode=True):
                print(f"✓ Created: {output_path}")
                return str(output_path)
        return None
    
    def cleanup_intermediate_files(self):
        """Clean up intermediate clip files, keeping only final candidate videos"""
        print("Cleaning up intermediate files...")
        
        # Keep only these final candidate files
        keep_files = {
            "candidate_1_all_clips.mp4",
            "candidate_2_high_score.mp4", 
            "candidate_3_short_clips.mp4",
            "candidate_4_best_hooks.mp4",
            "candidate_5_chronological.mp4",
            "candidate_6_segments.mp4",
            "candidate_7_no_promo.mp4",
            "candidates_summary.txt"
        }
        
        removed_count = 0
        for file_path in self.output_dir.iterdir():
            if file_path.is_file() and file_path.name not in keep_files:
                try:
                    file_path.unlink()
                    removed_count += 1
                except Exception as e:
                    print(f"Warning: Could not remove {file_path.name}: {e}")
        
        print(f"Removed {removed_count} intermediate files")

    def create_all_candidates(self):
        """Create all candidate videos"""
        print(f"Creating candidate videos from {self.input_video}")
        print(f"Output directory: {self.output_dir}")
        print("-" * 50)
        
        candidates = []
        
        # Only create the chronological candidate (single output)
        candidate_methods = [
            self.create_candidate_5_chronological,
        ]
        
        for method in candidate_methods:
            try:
                result = method()
                if result:
                    candidates.append(result)
            except Exception as e:
                print(f"Error creating candidate: {e}")
        
        # Clean up intermediate files
        self.cleanup_intermediate_files()
        
        print("-" * 50)
        print(f"Created {len(candidates)} candidate videos:")
        for candidate in candidates:
            print(f"  - {candidate}")
        
        # Create a summary file
        self.create_summary_file(candidates)
        
        return candidates
    
    def create_summary_file(self, candidates: List[str]):
        """Create a summary file with details about each candidate"""
        summary_path = self.output_dir / "candidates_summary.txt"
        
        with open(summary_path, 'w') as f:
            f.write("Video Candidates Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source video: {self.input_video}\n")
            f.write(f"Sample data: {self.sample_output_path}\n\n")
            
            f.write("Original Clips Analysis:\n")
            f.write("-" * 30 + "\n")
            for i, clip in enumerate(self.clips):
                f.write(f"Clip {i+1} (Rank {clip['rank']}):\n")
                f.write(f"  Time: {clip['start']:.2f}s - {clip['end']:.2f}s ({clip['duration']:.2f}s)\n")
                f.write(f"  Score: {clip['score']:.2f}\n")
                f.write(f"  Hooks: {', '.join(clip['reasons']['hook'])}\n")
                f.write(f"  Penalties: {', '.join(clip['reasons'].get('penalties', []))}\n")
                f.write(f"  Preview: {clip['preview_text'][:100]}...\n\n")
            
            f.write("Generated Candidates:\n")
            f.write("-" * 30 + "\n")
            candidate_descriptions = [
                "All top-ranked clips in order",
                "Only clips with score > 0.85",
                "Clips under 35 seconds for quick consumption",
                "Clips with the best hook types",
                "Clips in chronological order",
                "Individual segments instead of full clips",
                "Clips without promotional content"
            ]
            
            for i, (candidate, description) in enumerate(zip(candidates, candidate_descriptions)):
                f.write(f"Candidate {i+1}: {description}\n")
                f.write(f"  File: {candidate}\n\n")
        
        print(f"✓ Created summary: {summary_path}")

def main():
    parser = argparse.ArgumentParser(description='Create multiple candidate videos from clips')
    parser.add_argument('--input', '-i', 
                       default='input_videos/input.mp4',
                       help='Input video file path')
    parser.add_argument('--sample-output', '-s',
                       default='captions_out/sample_output.json',
                       help='Sample output JSON file path')
    parser.add_argument('--output-dir', '-o',
                       default='candidate_videos',
                       help='Output directory for candidate videos')
    
    args = parser.parse_args()
    
    # Check if input files exist
    if not os.path.exists(args.input):
        print(f"Error: Input video not found: {args.input}")
        return 1
    
    if not os.path.exists(args.sample_output):
        print(f"Error: Sample output file not found: {args.sample_output}")
        return 1
    
    # Check if FFmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: FFmpeg not found. Please install FFmpeg first.")
        return 1
    
    # Create the splicer and generate candidates
    splicer = VideoSplicer(args.input, args.sample_output, args.output_dir)
    candidates = splicer.create_all_candidates()
    
    if candidates:
        print(f"\n🎉 Successfully created {len(candidates)} candidate videos!")
        print(f"Check the '{args.output_dir}' directory for results.")
    else:
        print("\n❌ No candidate videos were created. Check the error messages above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
