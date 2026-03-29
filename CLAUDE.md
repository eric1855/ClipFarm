# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

ClipFarm is an AI-powered long-form to short-form video content generator. Upload a video, it transcribes with Whisper, uses GPT to pick the best clip-worthy moments, then renders them as individual MP4s. Built at HackCMU 2025.

## Running the App

```bash
# One-time setup
./setup.sh                    # creates venv, installs pip deps, checks ffmpeg

# Start everything (recommended)
./start-all.sh                # launches backend + frontend with trap handlers

# Or start separately
./start-backend.sh            # FastAPI on :8000 (auto-creates venv)
./start-frontend.sh           # Express on :3000
```

Manual start:
```bash
# Backend
source .venv/bin/activate
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload

# Frontend
npm start                     # or: npm run dev (nodemon)
```

Rebuild Tailwind CSS: `npm run build-css`

Open http://localhost:3000 in browser.

## Architecture

Two-server setup: Express frontend (port 3000) proxies API calls to FastAPI backend (port 8000).

**Frontend → Backend proxy** (`server.js`): Routes `/api/upload` (10-min timeout), `/api/download/:jobId/:filename`, `/api/jobs/:jobId`, `/api/health` are proxied via axios. Static files served from `./public`. Media files served from `output_videos/` at `/media/output/` and `candidate_videos/` at `/media/candidates/`.

**Processing pipeline** (all runs in single `POST /upload?model=small` call):
1. **Transcribe** — faster-whisper locally, outputs segments with timestamps
2. **Select clips** — Gemini 2.5 Flash ranks segments using `artifacts/system_prompt.txt`. Returns up to 10 clips, max 30s total, 2-5s each, no overlaps
3. **Generate candidates** — `video_splicer.py` uses FFmpeg to produce 7 candidate MP4s (all_clips, high_score, short_clips, best_hooks, chronological, segments, no_promo) + promotes chronological to `output_videos/` as final video
4. **Download** (`GET /download/{job_id}/{filename}`) — transcript.txt, segments.json, words.json, .srt, .vtt

**Frontend displays:** Final video player, 7 candidate video cards with playback/download, 5 transcript download links. Progress bar simulates pipeline phases.

**Backend modules:**
- `backend/api.py` — all FastAPI routes, request/response models, orchestration logic, Gemini integration via `_gemini_chat()`
- `backend/extra_captions.py` — Whisper transcription and caption file generation
- `backend/video_splicer.py` — FFmpeg-based clip extraction and concatenation

## Key Config

Environment variables in `.env`:
- `GEMINI_API_KEY` — required for clip selection via Gemini
- `GEMINI_MODEL` — default `gemini-2.5-flash`
- `SYSTEM_PROMPT_FILE` — path to clip selection prompt (`artifacts/system_prompt.txt`)
- `ALLOW_SERVER_TRANSCRIPTION` — `0` prefers local faster-whisper, `1` uses OpenAI API
- `CT2_FORCE_CPU` — set `1` on Windows without CUDA

## Gemini Integration Notes

- Clip selection uses the **native Google GenAI SDK** (`google-genai`), NOT the OpenAI-compatible endpoint (which silently caps output tokens).
- `_get_client()` returns a `genai.Client` if `GEMINI_API_KEY` is set, falls back to OpenAI if `OPENAI_API_KEY` is set instead.
- `_gemini_chat()` handles message format conversion (OpenAI-style messages → Gemini format) and strips markdown code fences from responses.
- **Critical:** Gemini 2.5 Flash uses "thinking" tokens that consume the output budget. Must set `thinking_budget=0` in `ThinkingConfig` or responses get truncated.
- The `/upload` endpoint (legacy path with `?model=` param) uses native Gemini. Other endpoints (`/clips/select`, `/chat`, `/process`) still use the OpenAI client and would need updating if used.

## Frontend Theme

Terminal hacker aesthetic: CRT scanline overlay, vignette, matrix rain background, green-on-black. The entire UI lives inside a `.terminal-window` div that is draggable by its titlebar (implemented in `public/js/draggable.js`). Glass cursor effect on titlebar text. Tailwind CSS with custom styles in `public/css/input.css` → rebuild with `npm run build-css`.

## System Requirements

- Python 3.7+, Node.js 16+, FFmpeg (required for all video/audio processing)
- `google-genai` Python package (for Gemini clip selection)
