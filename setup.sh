#!/bin/bash
# Setup script for caption extraction

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Checking FFmpeg installation..."
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg not found. Please install FFmpeg:"
    echo "  macOS: brew install ffmpeg"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  Windows: Download from https://ffmpeg.org/download.html"
    exit 1
else
    echo "FFmpeg is installed ✓"
fi

echo "Setup complete! You can now run:"
echo "python frontend/extra_captions.py your_video.mp4 --outdir captions_out --model small --compute-type int8"
