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
    def __init__(self, input_video: str, sample_output_path: str, output_dir: str = "candidate_videos",
                 words_data: List[Dict] = None, transition_titles: List[str] = None):
        self.input_video = input_video
        self.sample_output_path = sample_output_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.words_data = words_data or []
        self.transition_titles = transition_titles or []

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
    
    def _get_video_info(self):
        """Get source video width, height, and fps using ffprobe."""
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_streams', '-select_streams', 'v:0', self.input_video
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(r.stdout)
            stream = info['streams'][0]
            w = int(stream['width'])
            h = int(stream['height'])
            # Parse fps from r_frame_rate like "30/1" or "30000/1001"
            num, den = stream.get('r_frame_rate', '30/1').split('/')
            fps = round(int(num) / int(den))
            return w, h, fps
        except Exception:
            return 1920, 1080, 30  # sensible defaults

    def _generate_clip_srt(self, clip: Dict, output_path: str) -> bool:
        """Generate an SRT file for a single clip using word-level timestamps."""
        if not self.words_data:
            return False

        clip_start = clip['start']
        clip_end = clip['end']

        # Filter words within clip range
        clip_words = [w for w in self.words_data if w.get('start', 0) >= clip_start - 0.05 and w.get('end', 0) <= clip_end + 0.05]
        if not clip_words:
            return False

        # Group words into subtitle lines (max 5 words per line)
        subtitles = []
        group = []
        for word in clip_words:
            group.append(word)
            text_so_far = ' '.join(w.get('word', w.get('text', '')) for w in group)
            is_punctuation_break = text_so_far.rstrip().endswith(('.', '!', '?', '…', ';', ':'))
            if len(group) >= 5 or is_punctuation_break:
                subtitles.append({
                    'start': group[0].get('start', 0) - clip_start,
                    'end': group[-1].get('end', 0) - clip_start,
                    'text': text_so_far.strip()
                })
                group = []
        if group:
            subtitles.append({
                'start': group[0].get('start', 0) - clip_start,
                'end': group[-1].get('end', 0) - clip_start,
                'text': ' '.join(w.get('word', w.get('text', '')) for w in group).strip()
            })

        # Ensure no negative timestamps
        for s in subtitles:
            s['start'] = max(0.0, s['start'])
            s['end'] = max(s['start'] + 0.1, s['end'])

        # Write SRT
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, sub in enumerate(subtitles, 1):
                start_ts = self._format_srt_ts(sub['start'])
                end_ts = self._format_srt_ts(sub['end'])
                f.write(f"{i}\n{start_ts} --> {end_ts}\n{sub['text']}\n\n")
        return True

    def _format_srt_ts(self, seconds: float) -> str:
        """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace('.', ',')

    def _generate_title_card(self, text: str, duration: float, output_path: str,
                              width: int, height: int, fps: int) -> bool:
        """Generate a title card MP4: text centered on black background with silent audio."""
        # Escape special chars for FFmpeg drawtext
        escaped = text.replace("'", "'\\''").replace(":", "\\:").replace("%", "%%")
        font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        fontsize = max(36, min(64, width // 20))

        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=c=black:s={width}x{height}:d={duration}:r={fps}',
            '-f', 'lavfi', '-i', f'anullsrc=r=44100:cl=stereo',
            '-vf', (
                f"drawtext=text='{escaped}':"
                f"fontfile='{font_path}':"
                f"fontsize={fontsize}:"
                f"fontcolor=white:"
                f"x=(w-text_w)/2:y=(h-text_h)/2:"
                f"shadowcolor=black:shadowx=2:shadowy=2"
            ),
            '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '128k',
            '-shortest',
            str(output_path)
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating title card: {e.stderr}")
            return False

    def extract_clip(self, start: float, end: float, output_path: str, subtitle_path: str = None) -> bool:
        """Extract a single clip using FFmpeg with fallbacks.

        Try stream copy first; if it fails (e.g., non-keyframe start), fall back to re-encode.
        """
        start_time = self.format_time(start)
        duration = max(0.0, end - start)

        # If subtitles requested, go straight to re-encode with subtitle filter
        if subtitle_path and os.path.exists(subtitle_path):
            # Escape path for FFmpeg filter (colons and backslashes)
            escaped_sub = subtitle_path.replace('\\', '/').replace(':', '\\:')
            sub_style = "FontSize=24,Alignment=2,MarginV=30,BorderStyle=3,Outline=2,Shadow=1,Bold=1,Fontname=Arial"
            cmd_sub = [
                'ffmpeg', '-y',
                '-ss', start_time,
                '-t', str(duration),
                '-i', self.input_video,
                '-vf', f"subtitles='{escaped_sub}':force_style='{sub_style}'",
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                '-c:a', 'aac', '-b:a', '128k',
                output_path
            ]
            try:
                subprocess.run(cmd_sub, capture_output=True, text=True, check=True)
                return True
            except subprocess.CalledProcessError as e:
                print(f"Subtitle burn failed, extracting without subs: {e.stderr[:200]}")
                # Fall through to normal extraction

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
        """Candidate 5: Clips in chronological order with burned captions and title cards."""
        print("Creating Candidate 5: Chronological order (enhanced)...")

        chronological_clips = sorted(self.clips, key=lambda x: x['start'])
        has_titles = bool(self.transition_titles)
        has_words = bool(self.words_data)

        # Get source video dimensions for title cards
        if has_titles:
            width, height, fps = self._get_video_info()

        final_paths = []
        for i, clip in enumerate(chronological_clips):
            # Insert title card before each clip
            if has_titles and i < len(self.transition_titles) and self.transition_titles[i]:
                title_path = self.output_dir / f"title_{i+1}.mp4"
                if self._generate_title_card(self.transition_titles[i], 2.0, str(title_path), width, height, fps):
                    final_paths.append(str(title_path))

            # Generate per-clip SRT for subtitle burn-in
            srt_path = None
            if has_words:
                srt_file = self.output_dir / f"chrono_clip_{i+1}.srt"
                if self._generate_clip_srt(clip, str(srt_file)):
                    srt_path = str(srt_file)

            # Extract clip (with subtitles if available)
            clip_path = self.output_dir / f"chrono_clip_{i+1}.mp4"
            if self.extract_clip(clip['start'], clip['end'], str(clip_path), subtitle_path=srt_path):
                final_paths.append(str(clip_path))

        if final_paths:
            output_path = self.output_dir / "candidate_5_chronological.mp4"
            if self.concatenate_videos(final_paths, str(output_path), encode=True):
                print(f"✓ Created: {output_path} (with {'captions' if has_words else 'no captions'}, {'titles' if has_titles else 'no titles'})")
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
        
        # Create all candidates
        candidate_methods = [
            self.create_candidate_1_top_clips,
            self.create_candidate_2_high_score,
            self.create_candidate_3_short_clips,
            self.create_candidate_4_best_hooks,
            self.create_candidate_5_chronological,
            self.create_candidate_6_trimmed_segments,
            self.create_candidate_7_no_promo
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
