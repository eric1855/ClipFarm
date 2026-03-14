# Full End-to-End AI Video Clipper

A full-stack web application that extracts captions and timestamps from video/audio files using faster-whisper for automatic speech recognition (ASR). Features a FastAPI backend and a modern Node.js frontend with Tailwind CSS.

## Features

- **Web Interface**: Modern, responsive UI built with Tailwind CSS
- **FastAPI Backend**: RESTful API with automatic documentation
- **Multiple Output Formats**:
  - `transcript.txt` - Full text transcript
  - `segments.json` - Segments with timestamps
  - `words.json` - Individual words with timestamps
  - `transcript.srt` - SRT subtitle file
  - `transcript.vtt` - VTT subtitle file
- **Smart subtitle grouping** - Optimized for mobile viewing (6 words max per caption)
- **Configurable Processing**: Support for multiple Whisper model sizes
- **Voice Activity Detection**: Optional VAD filtering
- **CPU/GPU Support**: Optimized processing options
- **File Upload**: Drag-and-drop interface with progress tracking
- **LLM Integration**: AI-powered clip selection and processing

## Requirements

- Python 3.7+
- Node.js 16+ and npm
- FFmpeg (for audio/video processing)

## Quick Start

### Option 1: Start Everything at Once

```bash
# Make scripts executable (if not already)
chmod +x start-*.sh

# Start both backend and frontend
./start-all.sh
```

### Option 2: Start Backend and Frontend Separately

```bash
# Terminal 1: Start Backend
./start-backend.sh

# Terminal 2: Start Frontend (in a new terminal)
./start-frontend.sh
```

## Installation

1. **Clone or download this repository**

2. **Install FFmpeg:**
   - **macOS:** `brew install ffmpeg`
   - **Ubuntu/Debian:** `sudo apt install ffmpeg`
   - **Windows:** Download from https://ffmpeg.org/download.html

3. **Install Node.js:**
   - Visit https://nodejs.org/ and download the LTS version
   - Or use a package manager like `brew install node` (macOS)

4. **The start scripts will automatically install Python and Node.js dependencies**

## Application Architecture

### Backend (FastAPI)
- **Port**: 8000
- **Framework**: FastAPI with Uvicorn
- **Features**: 
  - File upload handling
  - Caption extraction using faster-whisper
  - RESTful API with automatic documentation
  - CORS support for frontend communication
  - Job-based processing with unique IDs

### Frontend (Node.js + Express)
- **Port**: 3000
- **Framework**: Express.js serving static files
- **Styling**: Tailwind CSS with custom components
- **Features**:
  - Drag-and-drop file upload
  - Real-time progress tracking
  - Responsive design
  - Download management
  - Error handling and user feedback

### File Structure
```
├── main.py                 # FastAPI backend server
├── server.js              # Express.js frontend server
├── extract_captions.py    # Core caption extraction logic
├── package.json           # Node.js dependencies
├── requirements.txt       # Python dependencies
├── tailwind.config.js     # Tailwind CSS configuration
├── public/                # Frontend assets
│   ├── index.html         # Main HTML template
│   ├── css/               # CSS files
│   └── js/                # JavaScript files
├── uploads/               # Temporary upload directory
├── captions_out/          # Generated caption files
└── start-*.sh            # Deployment scripts
```

## Usage

### Web Interface

1. **Start the application** using one of the methods above
2. **Open your browser** and go to `http://localhost:3000`
3. **Upload a file** by dragging and dropping or clicking to browse
4. **Configure options**:
   - **Model**: Choose Whisper model size (tiny=fastest, large=most accurate)
   - **Language**: Select language or leave auto-detect
   - **Compute Type**: Choose CPU or GPU processing
   - **VAD**: Enable voice activity detection for better accuracy
5. **Click "Extract Captions"** and wait for processing
6. **Download results** in various formats (TXT, JSON, SRT, VTT)

### API Usage

The backend provides a REST API at `http://localhost:8000`:

- **API Documentation**: `http://localhost:8000/docs`
- **Health Check**: `GET /health`
- **Upload File**: `POST /upload`
- **Download Files**: `GET /download/{job_id}/{filename}`

### Command Line Usage (Legacy)

You can still use the original command-line script:

```bash
python frontend/extra_captions.py input_videos/input.mp4 --outdir captions_out --model small --compute-type int8
```

**Note:** The script now generates better subtitle grouping with fewer words per caption (6 words max) for improved readability on mobile devices and social media platforms.

### Command Line Arguments

- `input` (required): Path to input video/audio file
- `--outdir`: Output directory (default: `captions_out`)
- `--model`: Whisper model size (default: `small`)
  - Options: `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3`
- `--language`: Language code (e.g., `en`, `es`, `fr`). Auto-detects if not specified
- `--compute-type`: Compute type (default: `int8_float16`)
  - Options: `float16`, `int8_float16`, `int8`
  - Use `int8` for CPU-only processing
- `--beam-size`: Beam size for decoding (default: `5`)
- `--vad`: Enable voice activity detection filtering

### Examples

```bash
# Basic usage with small model
python frontend/extra_captions.py video.mp4

# Use tiny model for faster processing
python frontend/extra_captions.py video.mp4 --model tiny --compute-type int8

# Specify language and output directory
python frontend/extra_captions.py video.mp4 --language en --outdir my_captions --model medium

# Enable VAD filtering
python frontend/extra_captions.py video.mp4 --vad --model small --compute-type int8
```

## Project Structure

```
.
├─ backend/                # FastAPI app and APIs
│  ├─ __init__.py
│  └─ api.py               # Chat, stream, clips/select, process/sample
├─ frontend/               # CLI and (future) UI assets
│  ├─ __init__.py
│  └─ extra_captions.py    # Caption extraction CLI (moved)
├─ artifacts/
│  └─ system_prompt.txt    # System prompt used for clip selection
├─ captions_out/           # Generated outputs (ignored in VCS)
├─ input_videos/           # Optional input media folder (ignored in VCS)
├─ requirements.txt        # Python dependencies
├─ setup.sh                # Installer helper
├─ .env                    # Local environment (API keys, config)
└─ README.md
```

Note: `extract_captions.py` remains as a thin shim that delegates to
`frontend/extra_captions.py` to preserve existing commands.
## Output Files

The script generates 5 files in the output directory:

1. **`transcript.txt`** - Full text transcript
2. **`segments.json`** - Array of segments with start/end times and text
3. **`words.json`** - Array of individual words with timestamps
4. **`transcript.srt`** - SRT subtitle format
5. **`transcript.vtt`** - VTT subtitle format

## Overlaying Subtitles onto Video

After extracting captions, you can overlay them onto your video using FFmpeg:

### Basic Subtitle Overlay

```bash
ffmpeg -i input_videos/input.mp4 -vf "subtitles=captions_out/transcript.srt" -c:a copy output_with_subtitles.mp4
```

### Styled Subtitles (Recommended)

```bash
ffmpeg -i input_videos/input.mp4 -vf "subtitles=captions_out/transcript.srt:force_style='FontName=Helvetica,FontSize=24,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2,Alignment=2'" -c:a copy output_with_subtitles.mp4
```

### Subtitle Styling Options

You can customize the appearance by modifying the `force_style` parameter:

- `FontName`: Font family (e.g., `Helvetica`, `Arial-Bold`, `Roboto`)
- `FontSize`: Font size in pixels (20-28 recommended)
- `PrimaryColour`: Text color in BGR hex format (`&HFFFFFF&` = white)
- `OutlineColour`: Outline color (`&H000000&` = black)
- `Outline`: Outline thickness (1-3 recommended)
- `Alignment`: Text position (2 = bottom center)

### Example: Custom Styled Subtitles

```bash
ffmpeg -i input_videos/input.mp4 -vf "subtitles=captions_out/transcript.srt:force_style='FontName=Roboto,FontSize=26,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2,Alignment=2'" -c:a copy output_styled_subtitles.mp4
```

## Model Performance

| Model    | Speed           | Accuracy | Best For         |
| -------- | --------------- | -------- | ---------------- |
| `tiny`   | ~2x real-time   | Good     | Quick processing |
| `base`   | ~1x real-time   | Better   | Balanced         |
| `small`  | ~0.5x real-time | Good     | Recommended      |
| `medium` | ~0.3x real-time | Better   | High accuracy    |
| `large`  | ~0.2x real-time | Best     | Maximum accuracy |

## Troubleshooting

### Common Issues

1. **"faster-whisper not installed"**

   ```bash
   pip install faster-whisper
   ```

2. **"FFmpeg not found"**

   - macOS: `brew install ffmpeg`
   - Ubuntu/Debian: `sudo apt install ffmpeg`
   - Windows: Download from https://ffmpeg.org/download.html

3. **"int8_float16 compute type not supported"**

   - Use `--compute-type int8` for CPU-only processing

4. **No progress bar**
   - This is normal for the standard Whisper library
   - Check CPU usage to verify processing is happening

### Performance Tips

- Use `--model tiny` for fastest processing
- Use `--compute-type int8` for CPU-only processing
- Use `--vad` to filter out silence and improve accuracy
- For long videos, consider using a smaller model

## License

This project is open source and available under the MIT License.
<!-- achievement -->
<!-- achievement -->
