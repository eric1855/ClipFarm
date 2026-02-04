#!/usr/bin/env python3
"""
Caption extraction script using faster-whisper for ASR.
Extracts transcripts and timestamps from video/audio files.
"""

import argparse
import json
import os
import sys
import tempfile
import warnings
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Suppress deprecation warning from pkg_resources via ctranslate2 import path
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
)

try:
    from faster_whisper import WhisperModel
except ImportError:
    print("Error: faster-whisper not installed. Run: pip install faster-whisper")
    sys.exit(1)

def _ensure_ffmpeg_available() -> None:
    """Ensure FFmpeg is available; fall back to imageio-ffmpeg wrapper if needed."""
    try:
        import subprocess
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return
    except Exception:
        pass

    # Fallback: try imageio-ffmpeg to get a bundled binary
    try:
        import subprocess
        import shutil
        import imageio_ffmpeg  # type: ignore

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        wrapper_dir = Path(tempfile.gettempdir()) / "ffmpeg_wrapper"
        wrapper_dir.mkdir(parents=True, exist_ok=True)

        if os.name == "nt":
            # Copy to ffmpeg.exe so subprocess (and libraries) can execute without shell=True
            wrapper_path = wrapper_dir / "ffmpeg.exe"
            if not wrapper_path.exists():
                try:
                    shutil.copyfile(ffmpeg_exe, wrapper_path)
                except Exception:
                    # As a fallback, still try a .bat wrapper
                    wrapper_path = wrapper_dir / "ffmpeg.bat"
                    bat_content = f'@echo off\r\n"{ffmpeg_exe}" %*\r\n'
                    with open(wrapper_path, 'w', encoding='utf-8') as f:
                        f.write(bat_content)
        else:
            # POSIX: create a small shim script if symlink fails
            wrapper_path = wrapper_dir / "ffmpeg"
            if not wrapper_path.exists():
                try:
                    os.symlink(ffmpeg_exe, wrapper_path)
                except Exception:
                    sh_content = f'#!/usr/bin/env bash\n"{ffmpeg_exe}" "$@"\n'
                    with open(wrapper_path, 'w', encoding='utf-8') as f:
                        f.write(sh_content)
                    try:
                        os.chmod(wrapper_path, 0o755)
                    except Exception:
                        pass

        # Prepend wrapper directory to PATH so `ffmpeg` resolves
        os.environ["PATH"] = str(wrapper_dir) + os.pathsep + os.environ.get("PATH", "")
        # Also tell libraries explicitly
        os.environ["FFMPEG_BINARY"] = str(wrapper_path)
        os.environ.setdefault("IMAGEIO_FFMPEG_EXE", ffmpeg_exe)

        # Verify both direct exe and generic name
        try:
            subprocess.run([str(wrapper_path), '-version'], capture_output=True, check=True)
        except Exception:
            pass

        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return
    except Exception:
        pass

    # Still unavailable: show guidance and exit
    print("Error: FFmpeg not found. FFmpeg is required to process audio/video files.")
    print("Install FFmpeg:")
    print("  macOS: brew install ffmpeg")
    print("  Ubuntu/Debian: sudo apt install ffmpeg")
    print("  Windows: winget install Gyan.FFmpeg  (or download from https://ffmpeg.org/download.html)")
    print("Optionally: pip install imageio-ffmpeg to use a bundled FFmpeg.")
    sys.exit(1)


_ensure_ffmpeg_available()

def format_srt_timestamp(seconds: float) -> str:
    """Format timestamp for SRT format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"


def format_vtt_timestamp(seconds: float) -> str:
    """Format timestamp for VTT format (HH:MM:SS.mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millisecs:03d}"


def interpolate_word_timestamps(segment: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Interpolate word timestamps evenly within segment if missing."""
    start_time = segment['start']
    end_time = segment['end']
    text = segment['text'].strip()
    words = text.split()
    
    if not words:
        return []
    
    # Evenly distribute words across the segment duration
    duration = end_time - start_time
    word_duration = duration / len(words)
    
    interpolated_words = []
    for i, word in enumerate(words):
        word_start = start_time + (i * word_duration)
        word_end = start_time + ((i + 1) * word_duration)
        interpolated_words.append({
            'text': word,
            'start': word_start,
            'end': word_end
        })
    
    return interpolated_words


def group_text_for_subtitles(words: List[Dict[str, Any]], max_words: int = 6) -> List[Dict[str, Any]]:
    """Group words into subtitle lines with better breaks for mobile viewing."""
    if not words:
        return []
    
    groups = []
    current_group = []
    current_word_count = 0
    
    for i, word in enumerate(words):
        current_group.append(word)
        current_word_count += 1
        
        # Better break conditions for mobile-friendly subtitles
        should_break = (
            current_word_count >= max_words or  # Shorter max words (6 instead of 8)
            word['text'].rstrip('.,!?;:').endswith(('.', '!', '?', '…', ',', ';', ':')) or  # More punctuation breaks
            (current_word_count >= 3 and word['text'].rstrip('.,!?;:').endswith(('.', '!', '?'))) or  # Break on sentences even if short
            word == words[-1]  # Always break on last word
        )
        
        if should_break:
            if current_group:
                start_time = current_group[0]['start']
                end_time = current_group[-1]['end']
                text = ' '.join(w['text'] for w in current_group)
                
                # Ensure minimum display time (1.5 seconds)
                min_duration = 1.5
                if end_time - start_time < min_duration:
                    end_time = start_time + min_duration
                
                groups.append({
                    'start': start_time,
                    'end': end_time,
                    'text': text
                })
                
                current_group = []
                current_word_count = 0
    
    return groups


def write_srt_file(segments: List[Dict[str, Any]], output_path: Path) -> None:
    """Write SRT subtitle file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments, 1):
            start_time = format_srt_timestamp(segment['start'])
            end_time = format_srt_timestamp(segment['end'])
            text = segment['text']
            
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n\n")


def write_vtt_file(segments: List[Dict[str, Any]], output_path: Path) -> None:
    """Write VTT subtitle file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        
        for segment in segments:
            start_time = format_vtt_timestamp(segment['start'])
            end_time = format_vtt_timestamp(segment['end'])
            text = segment['text']
            
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n\n")


def extract_captions(
    input_path: str,
    outdir: str,
    model: str,
    language: Optional[str],
    compute_type: str,
    beam_size: int,
    vad: bool
) -> None:
    """Extract captions from media file using faster-whisper."""
    
    # Create output directory
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Force CPU to avoid CUDA/cuDNN issues on machines without GPU libs
    os.environ.setdefault("CT2_FORCE_CPU", "1")
    # Initialize Whisper model on CPU explicitly
    print("Transcription mode: faster-whisper via extra_captions.py (local)")
    print(f"Loading model: {model} (compute_type: {compute_type})")
    whisper_model = WhisperModel(model, device="cpu", compute_type=compute_type)
    
    # Transcribe with word timestamps
    print("Transcribing...")
    segments, info = whisper_model.transcribe(
        input_path,
        language=language,
        beam_size=beam_size,
        word_timestamps=True,
        vad_filter=vad
    )
    
    # Convert to lists and extract data
    segments_list = list(segments)
    words_list = []
    segments_data = []
    
    for segment in segments_list:
        segment_data = {
            'start': segment.start,
            'end': segment.end,
            'text': segment.text.strip()
        }
        segments_data.append(segment_data)
        
        # Extract words from segment
        if hasattr(segment, 'words') and segment.words:
            for word in segment.words:
                words_list.append({
                    'text': word.word,
                    'start': word.start,
                    'end': word.end
                })
        else:
            # Fallback: interpolate word timestamps
            interpolated_words = interpolate_word_timestamps(segment_data)
            words_list.extend(interpolated_words)
    
    # Check if we have any content
    if not segments_data:
        raise RuntimeError("No transcription content found. The audio may be too short or silent.")
    
    # Generate full transcript
    full_transcript = ' '.join(segment['text'] for segment in segments_data)
    
    # Group words for subtitles
    subtitle_groups = group_text_for_subtitles(words_list)
    
    # Write output files
    print("Writing output files...")
    
    # transcript.txt
    with open(output_dir / 'transcript.txt', 'w', encoding='utf-8') as f:
        f.write(full_transcript)
    
    # segments.json
    with open(output_dir / 'segments.json', 'w', encoding='utf-8') as f:
        json.dump(segments_data, f, indent=2, ensure_ascii=False)
    
    # words.json
    with open(output_dir / 'words.json', 'w', encoding='utf-8') as f:
        json.dump(words_list, f, indent=2, ensure_ascii=False)
    
    # transcript.srt
    write_srt_file(subtitle_groups, output_dir / 'transcript.srt')
    
    # transcript.vtt
    write_vtt_file(subtitle_groups, output_dir / 'transcript.vtt')
    
    # Print summary
    print(f"\nCaption extraction completed!")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"Files created:")
    print(f"  - transcript.txt ({len(full_transcript)} characters)")
    print(f"  - segments.json ({len(segments_data)} segments)")
    print(f"  - words.json ({len(words_list)} words)")
    print(f"  - transcript.srt ({len(subtitle_groups)} subtitle lines)")
    print(f"  - transcript.vtt ({len(subtitle_groups)} subtitle lines)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract captions and timestamps from media files using faster-whisper"
    )
    
    parser.add_argument(
        'input',
        help='Path to input video/audio file'
    )
    
    parser.add_argument(
        '--outdir',
        default='captions_out',
        help='Output directory (default: captions_out)'
    )
    
    parser.add_argument(
        '--model',
        default='small',
        choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'],
        help='Whisper model size (default: small)'
    )
    
    parser.add_argument(
        '--language',
        default=None,
        help='Language code (e.g., en, es, fr). Auto-detect if not specified'
    )
    
    parser.add_argument(
        '--compute-type',
        default='int8_float16',
        choices=['float16', 'int8_float16', 'int8'],
        help='Compute type (default: int8_float16, use int8 for CPU-only)'
    )
    
    parser.add_argument(
        '--beam-size',
        type=int,
        default=5,
        help='Beam size for decoding (default: 5)'
    )
    
    parser.add_argument(
        '--vad',
        action='store_true',
        help='Enable voice activity detection filtering'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' not found.")
        sys.exit(1)
    
    try:
        extract_captions(
            input_path=args.input,
            outdir=args.outdir,
            model=args.model,
            language=args.language,
            compute_type=args.compute_type,
            beam_size=args.beam_size,
            vad=args.vad
        )
    except Exception as e:
        print(f"Error during caption extraction: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
