"""
FastAPI app that proxies chat requests to OpenAI models.

Endpoints:
- GET /health: basic health check
- POST /chat: send a message or messages to GPT and get a reply
- POST /chat/stream: stream GPT's reply as plain text chunks

Requires env var `ANTHROPIC_API_KEY`.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional, Union

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse, FileResponse
from pydantic import BaseModel, Field
import subprocess
import shutil
import json
import tempfile
from copy import deepcopy
import uuid
from pathlib import Path
import warnings
import logging

try:
    # Load .env if available; ignore if package not installed
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

# Suppress ctranslate2/pkg_resources deprecation noise early (before imports)
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
)

logger = logging.getLogger("uvicorn.error")

try:
    # OpenAI client (kept for chat endpoints)
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

try:
    # Google GenAI SDK for Gemini clip selection
    from google import genai
    from google.genai import types as genai_types
except Exception:
    genai = None  # type: ignore
    genai_types = None  # type: ignore

try:
    # Faster-Whisper for transcription
    from faster_whisper import WhisperModel
except Exception as e:
    WhisperModel = None  # type: ignore

# Optional import of the full extraction writer to preserve legacy UI behavior
try:
    from backend.extra_captions import extract_captions as _extract_write_outputs  # type: ignore
except Exception:
    try:
        from extract_captions import extract_captions as _extract_write_outputs  # type: ignore
    except Exception:
        _extract_write_outputs = None  # type: ignore

# Video splicer utility (candidate video creation)
try:
    from backend.video_splicer import VideoSplicer  # type: ignore
except Exception:
    VideoSplicer = None  # type: ignore

def _get_videosplicer():
    """Return VideoSplicer class, attempting lazy import if needed.

    This guards against path/import-order issues under reloaders.
    """
    global VideoSplicer  # type: ignore
    if VideoSplicer is not None:
        return VideoSplicer
    try:
        from backend.video_splicer import VideoSplicer as VS  # type: ignore
        VideoSplicer = VS  # type: ignore
        logger.info("VideoSplicer loaded from backend.video_splicer")
        return VideoSplicer
    except Exception:
        try:
            from video_splicer import VideoSplicer as VS  # type: ignore
            VideoSplicer = VS  # type: ignore
            logger.info("VideoSplicer loaded from video_splicer (fallback)")
            return VideoSplicer
        except Exception as e:
            logger.warning(f"Unable to import VideoSplicer: {e}")
            return None


def _openai_transcribe_segments(input_path: str, model: Optional[str] = None) -> List[dict]:
    """Fallback transcription via OpenAI Whisper API.

    Returns a list of segments with keys: start, end, text.
    """
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set for fallback transcription")

    client = OpenAI(api_key=api_key)
    model_name = model or os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")
    logger.info(f"Transcription mode: OpenAI Whisper API (model={model_name})")
    with open(input_path, "rb") as f:
        # Request verbose JSON to get per-segment timestamps if available
        resp = client.audio.transcriptions.create(
            model=model_name,
            file=f,
            response_format="verbose_json",
            temperature=0,
        )

    segs: List[dict] = []
    # New SDK returns attributes on an object; ensure we can iterate
    raw_segments = getattr(resp, "segments", None) or []
    for s in raw_segments:
        try:
            start = float(getattr(s, "start", None) if hasattr(s, "start") else s.get("start", 0.0))
            end = float(getattr(s, "end", None) if hasattr(s, "end") else s.get("end", start))
            text = (getattr(s, "text", None) if hasattr(s, "text") else s.get("text", "")).strip()
            if end < start:
                end = start
            if text:
                segs.append({"start": start, "end": end, "text": text})
        except Exception:
            continue

    # If API didn't return segments, fallback to one segment with full text
    if not segs:
        full_text = (getattr(resp, "text", None) or "").strip()
        segs = [{"start": 0.0, "end": 0.0, "text": full_text}]
    return segs


def _openai_whisper_fallback_write_outputs(input_path: str, outdir: str) -> None:
    """Fallback path that transcribes using OpenAI and writes output files
    compatible with the legacy UI (transcript.txt, segments.json, words.json, srt, vtt).
    """
    # Import writer helpers if available
    write_srt = None
    write_vtt = None
    try:
        from frontend.extra_captions import write_srt_file as write_srt, write_vtt_file as write_vtt  # type: ignore
    except Exception:
        try:
            from extract_captions import write_srt_file as write_srt, write_vtt_file as write_vtt  # type: ignore
        except Exception:
            pass

    os.makedirs(outdir, exist_ok=True)
    logger.info("Fallback writer: generating legacy outputs from OpenAI Whisper API segments")
    segs = _openai_transcribe_segments(input_path)

    # transcript.txt
    full_text = " ".join(s.get("text", "").strip() for s in segs if s.get("text"))
    with open(os.path.join(outdir, "transcript.txt"), "w", encoding="utf-8") as f:
        f.write(full_text)

    # segments.json
    with open(os.path.join(outdir, "segments.json"), "w", encoding="utf-8") as f:
        import json as _json
        _json.dump(segs, f, ensure_ascii=False, indent=2)

    # words.json (fallback: empty)
    with open(os.path.join(outdir, "words.json"), "w", encoding="utf-8") as f:
        import json as _json
        _json.dump([], f, ensure_ascii=False, indent=2)

    # srt / vtt
    if write_srt and write_vtt:
        from pathlib import Path as _Path
        write_srt(segs, _Path(os.path.join(outdir, "transcript.srt")))
        write_vtt(segs, _Path(os.path.join(outdir, "transcript.vtt")))


DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_SYSTEM_PROMPT_FILE = os.getenv(
    "SYSTEM_PROMPT_FILE",
    os.path.join(BASE_DIR, "artifacts", "system_prompt.txt"),
)
DEFAULT_SAMPLE_INPUT = os.path.join(BASE_DIR, "input.mp4")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
ALLOW_SERVER_TRANSCRIPTION = os.getenv("ALLOW_SERVER_TRANSCRIPTION", "0").lower() in ("1", "true", "yes")
INPUT_VIDEOS_DIR = os.path.join(BASE_DIR, "input_videos")
CANDIDATE_VIDEOS_DIR = os.path.join(BASE_DIR, "candidate_videos")
FINAL_VIDEOS_DIR = os.path.join(BASE_DIR, "output_videos")


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    # Provide either `message` or `messages`
    message: Optional[str] = Field(None, description="Single user message")
    messages: Optional[List[Message]] = Field(
        None, description="Full conversation history"
    )
    system: Optional[str] = Field(None, description="System prompt/instructions")
    model: str = Field(DEFAULT_MODEL, description="GPT model name")
    max_tokens: int = Field(1024, ge=1, le=8192)
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    stream: bool = Field(False, description="Enable streaming response")


class ChatResponse(BaseModel):
    text: str
    model: str
    stop_reason: Optional[str] = None
    usage: Optional[dict] = None


def _build_messages(req: ChatRequest) -> List[dict]:
    if req.messages and len(req.messages) > 0:
        return [m.model_dump() for m in req.messages]
    if req.message:
        return [{"role": "user", "content": req.message}]
    raise HTTPException(status_code=400, detail="Provide `message` or `messages`.")


def _get_client():
    """Return a Google GenAI client for Gemini, or fall back to OpenAI client."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and genai is not None:
        return genai.Client(api_key=gemini_key)
    # Fallback to OpenAI if configured
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and OpenAI is not None:
        return OpenAI(api_key=openai_key)
    raise HTTPException(
        status_code=500,
        detail="GEMINI_API_KEY (or OPENAI_API_KEY) not set in environment.",
    )


def _gemini_chat(client, messages: list, model: str, max_tokens: int = 8192, temperature: float = 0.0) -> str:
    """Call Gemini via native SDK and return the text response."""
    # Convert OpenAI-style messages to Gemini format
    system_text = None
    contents = []
    for msg in messages:
        if msg["role"] == "system":
            system_text = msg["content"]
        else:
            contents.append(msg["content"])

    config = genai_types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=temperature,
        system_instruction=system_text,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )

    response = client.models.generate_content(
        model=model,
        contents="\n\n".join(contents),
        config=config,
    )
    # Debug: log finish reason
    if response.candidates:
        logger.info(f"Gemini finish_reason: {response.candidates[0].finish_reason}, token_count: {response.usage_metadata}")
    text = (response.text or "").strip()
    # Strip markdown code fences that Gemini wraps around JSON
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def _resolve_system_prompt(explicit: Optional[str]) -> Optional[str]:
    """Determine system prompt to use.

    Priority:
    1) explicit value from request body if provided and non-empty
    2) contents of file at SYSTEM_PROMPT_FILE (default artifacts/system_prompt.txt)
    3) env var SYSTEM_PROMPT if set
    4) None
    """
    if explicit and explicit.strip():
        return explicit

    # Try file
    path = os.getenv("SYSTEM_PROMPT_FILE", DEFAULT_SYSTEM_PROMPT_FILE)
    try:
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read().strip()
            if txt:
                return txt
    except FileNotFoundError:
        pass
    except Exception:
        # Ignore file errors, fall back to env
        pass

    # Fallback: env var string
    env_system = os.getenv("SYSTEM_PROMPT")
    if env_system and env_system.strip():
        return env_system
    return None


def _ensure_ffmpeg_available() -> None:
    """Ensure ffmpeg is invokable on PATH; try imageio-ffmpeg fallback on Windows/Linux.

    Raises HTTPException 500 if not available.
    """
    # First, try existing ffmpeg on PATH
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return
    except Exception:
        pass

    # Try imageio-ffmpeg fallback
    try:
        import imageio_ffmpeg  # type: ignore

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        wrapper_dir = os.path.join(tempfile.gettempdir(), "ffmpeg_wrapper_api")
        os.makedirs(wrapper_dir, exist_ok=True)

        if os.name == "nt":
            # Copy to ffmpeg.exe so subprocess can call directly
            target = os.path.join(wrapper_dir, "ffmpeg.exe")
            if not os.path.exists(target):
                shutil.copyfile(ffmpeg_exe, target)
        else:
            target = os.path.join(wrapper_dir, "ffmpeg")
            if not os.path.exists(target):
                try:
                    os.symlink(ffmpeg_exe, target)
                except Exception:
                    with open(target, "w", encoding="utf-8") as f:
                        f.write(f"#!/usr/bin/env bash\n\"{ffmpeg_exe}\" \"$@\"\n")
                    try:
                        os.chmod(target, 0o755)
                    except Exception:
                        pass

        os.environ["PATH"] = wrapper_dir + os.pathsep + os.environ.get("PATH", "")
        os.environ.setdefault("IMAGEIO_FFMPEG_EXE", ffmpeg_exe)
        os.environ.setdefault("FFMPEG_BINARY", target)

        subprocess.run([target, "-version"], capture_output=True, check=True)
        return
    except Exception:
        pass

    raise HTTPException(
        status_code=500,
        detail=(
            "FFmpeg not found. Install system ffmpeg or add imageio-ffmpeg."
        ),
    )


def _ensure_dirs() -> None:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(INPUT_VIDEOS_DIR, exist_ok=True)
    os.makedirs(CANDIDATE_VIDEOS_DIR, exist_ok=True)
    os.makedirs(FINAL_VIDEOS_DIR, exist_ok=True)


def _choose_candidate_by_keyword(candidate_dir: str, candidates: List[str], keyword: str) -> Optional[str]:
    """Pick a candidate video whose filename contains the keyword.

    Searches the provided candidates list first, then scans the directory.
    Returns the absolute path if found.
    """
    kw = keyword.lower()
    abs_candidates = [os.path.abspath(p) for p in candidates]
    for p in abs_candidates:
        name = os.path.basename(p).lower()
        if kw in name:
            return p
    try:
        for name in os.listdir(candidate_dir):
            if name.lower().endswith(".mp4") and kw in name.lower():
                return os.path.abspath(os.path.join(candidate_dir, name))
    except Exception:
        pass
    return None


def _promote_chronological_candidate_to_output(input_video_path: str, candidate_dir: str, candidates: List[str]) -> Optional[str]:
    """Copy the chronological candidate into output_videos with a friendly name.

    Name format: <input_stem>_chronological.mp4 (with numeric suffix to avoid overwrite)
    Returns the destination path, or None if no chronological candidate is found.
    """
    chrono_path = _choose_candidate_by_keyword(candidate_dir, candidates, "chronological")
    if not chrono_path or not os.path.exists(chrono_path):
        return None

    os.makedirs(FINAL_VIDEOS_DIR, exist_ok=True)
    stem = os.path.splitext(os.path.basename(input_video_path))[0]
    dest = os.path.join(FINAL_VIDEOS_DIR, f"{stem}_chronological.mp4")
    if os.path.exists(dest):
        n = 1
        while os.path.exists(os.path.join(FINAL_VIDEOS_DIR, f"{stem}_chronological_{n}.mp4")):
            n += 1
        dest = os.path.join(FINAL_VIDEOS_DIR, f"{stem}_chronological_{n}.mp4")
    try:
        shutil.copyfile(chrono_path, dest)
        logger.info(f"Promoted chronological candidate to {dest}")
        return dest
    except Exception as e:
        logger.warning(f"Failed to promote chronological candidate: {e}")
        return None


def _save_upload(file: UploadFile) -> dict:
    """Persist upload to disk with strict sequencing:

    1) Write the file to `input_videos/` using the original filename (unique-ified).
    2) Only after that completes, copy the file to `uploads/` under a uuid name.
    3) Return metadata including both paths.
    """
    _ensure_dirs()
    original_name = os.path.basename(file.filename or "upload.mp4")
    stem, ext = os.path.splitext(original_name)
    if not ext:
        ext = ".mp4"

    # Resolve unique path in input_videos first
    local_target = os.path.join(INPUT_VIDEOS_DIR, original_name)
    if os.path.exists(local_target):
        n = 1
        while os.path.exists(os.path.join(INPUT_VIDEOS_DIR, f"{stem}_{n}{ext}")):
            n += 1
        local_target = os.path.join(INPUT_VIDEOS_DIR, f"{stem}_{n}{ext}")

    # Stream write to input_videos (authoritative local copy)
    size = 0
    with open(local_target, "wb") as out:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            size += len(chunk)
        out.flush()
        os.fsync(out.fileno())
    logger.info(f"Saved input to {local_target} ({size} bytes)")

    # Now copy to uploads under a UUID name for backend tracking
    file_id = str(uuid.uuid4())
    dest = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    shutil.copyfile(local_target, dest)

    return {
        "file_id": file_id,
        "filename": file.filename,
        "path": dest,  # backend internal path
        "size": size,
        "local_copy": local_target,
    }


def _ffmpeg_extract_clip(input_path: str, output_path: str, start: float, end: float) -> None:
    _ensure_ffmpeg_available()
    duration = max(0.0, end - start)
    if duration <= 0:
        raise ValueError("Non-positive duration for clip")
    # Try stream copy for speed; fall back to re-encode if copy fails
    cmd_copy = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-to", f"{end:.3f}",
        "-i", input_path,
        "-c", "copy",
        output_path,
    ]
    try:
        subprocess.run(cmd_copy, check=True, capture_output=True)
        return
    except Exception:
        pass
    cmd_encode = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-to", f"{end:.3f}",
        "-i", input_path,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        output_path,
    ]
    subprocess.run(cmd_encode, check=True, capture_output=True)


def _force_cpu_for_ct2() -> None:
    """Force CTranslate2 to use CPU to avoid accidental CUDA path on Windows."""
    os.environ.setdefault("CT2_FORCE_CPU", "1")


def _normalize_compute_type(ct: Optional[str]) -> str:
    """Prefer CPU-safe compute types when GPU libraries are unavailable.

    On Windows, avoid float16 variants by default to prevent cuDNN errors.
    """
    if not ct:
        return "int8"
    val = str(ct).lower()
    if os.name == "nt" and ("float16" in val or val == "float16"):
        return "int8"
    return ct


def _transcribe_media(
    input_path: str,
    model_size: str = os.getenv("WHISPER_MODEL", "small"),
    language: Optional[str] = None,
    compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
    beam_size: int = 5,
    vad: bool = True,
) -> List[dict]:
    """Transcribe media file to segment list using faster-whisper.

    Returns a list of dicts with keys: start, end, text
    """
    if WhisperModel is None:
        raise HTTPException(
            status_code=500,
            detail="faster-whisper not installed. Install dependencies.",
        )
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail=f"Input not found: {input_path}")

    _ensure_ffmpeg_available()

    ct = _normalize_compute_type(compute_type)
    try:
        _force_cpu_for_ct2()
        model = WhisperModel(model_size, device="cpu", compute_type=ct)
        segments_iter, info = model.transcribe(
            input_path,
            language=language,
            beam_size=beam_size,
            word_timestamps=False,
            vad_filter=vad,
        )
        segments = list(segments_iter)
        if not segments:
            raise HTTPException(status_code=422, detail="No transcription content found.")
        out: List[dict] = []
        for s in segments:
            out.append({
                "start": float(getattr(s, "start", 0.0) or 0.0),
                "end": float(getattr(s, "end", 0.0) or 0.0),
                "text": (getattr(s, "text", "") or "").strip(),
            })
        return out
    except HTTPException:
        raise
    except Exception as e:
        # Retry once with CPU-safe compute type
        logger.info(f"Transcription local failed ({e}); retrying with compute_type=int8 on CPU")
        if ct != "int8":
            try:
                _force_cpu_for_ct2()
                model = WhisperModel(model_size, device="cpu", compute_type="int8")
                segments_iter, info = model.transcribe(
                    input_path,
                    language=language,
                    beam_size=beam_size,
                    word_timestamps=False,
                    vad_filter=vad,
                )
                segments = list(segments_iter)
                out: List[dict] = []
                for s in segments:
                    out.append({
                        "start": float(getattr(s, "start", 0.0) or 0.0),
                        "end": float(getattr(s, "end", 0.0) or 0.0),
                        "text": (getattr(s, "text", "") or "").strip(),
                    })
                logger.info("Transcription mode: faster-whisper (backend, CPU, int8)")
                return out
            except Exception as e2:
                try:
                    logger.info(f"Local retry failed ({e2}); falling back to OpenAI Whisper API")
                    return _openai_transcribe_segments(input_path)
                except Exception as fe:
                    raise HTTPException(status_code=500, detail=f"Transcription failed: {e2}; Fallback failed: {fe}")
        else:
            # Fallback to OpenAI Whisper API if available
            try:
                logger.info("Transcription mode: OpenAI Whisper API (backend fallback)")
                return _openai_transcribe_segments(input_path)
            except Exception as fe:
                raise HTTPException(status_code=500, detail=f"Transcription failed: {e}; Fallback failed: {fe}")


app = FastAPI(title="GPT Proxy API", version="0.1.0")

# Allow all origins by default; adjust as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": DEFAULT_MODEL, "server_transcription": ALLOW_SERVER_TRANSCRIPTION}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    client = _get_client()
    messages = _build_messages(req)

    try:
        # Prepare OpenAI messages with optional system at the front
        oai_messages: List[dict] = []
        system_text = _resolve_system_prompt(req.system)
        if system_text:
            oai_messages.append({"role": "system", "content": system_text})
        oai_messages.extend(messages)

        if req.stream:
            def text_stream():
                stream = client.chat.completions.create(
                    model=req.model,
                    messages=oai_messages,
                    max_tokens=req.max_tokens,
                    temperature=req.temperature,
                    top_p=req.top_p,
                    stream=True,
                )
                for chunk in stream:
                    try:
                        delta = chunk.choices[0].delta
                        if delta and getattr(delta, "content", None):
                            yield delta.content
                    except Exception:
                        continue

            return StreamingResponse(text_stream(), media_type="text/plain; charset=utf-8")

        # Non-streaming
        resp = client.chat.completions.create(
            model=req.model,
            messages=oai_messages,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            top_p=req.top_p,
        )

        full_text = resp.choices[0].message.content or ""
        usage = None
        if getattr(resp, "usage", None):
            usage = {
                "input_tokens": getattr(resp.usage, "prompt_tokens", None),
                "output_tokens": getattr(resp.usage, "completion_tokens", None),
                "total_tokens": getattr(resp.usage, "total_tokens", None),
            }

        return JSONResponse(
            ChatResponse(
                text=full_text,
                model=req.model,
                stop_reason=getattr(resp.choices[0], "finish_reason", None),
                usage=usage,
            ).model_dump()
        )

    except Exception as e:
        status = getattr(e, "status_code", None) or 500
        raise HTTPException(status_code=status, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """Stream GPT response as plain text chunks.

    Accepts the same body as `/chat`; the `stream` flag is ignored here.
    """
    client = _get_client()
    messages = _build_messages(req)

    try:
        def text_stream():
            oai_messages: List[dict] = []
            system_text = _resolve_system_prompt(req.system)
            if system_text:
                oai_messages.append({"role": "system", "content": system_text})
            oai_messages.extend(messages)
            stream = client.chat.completions.create(
                model=req.model,
                messages=oai_messages,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
                top_p=req.top_p,
                stream=True,
            )
            for chunk in stream:
                try:
                    delta = chunk.choices[0].delta
                    if delta and getattr(delta, "content", None):
                        yield delta.content
                except Exception:
                    continue

        return StreamingResponse(text_stream(), media_type="text/plain; charset=utf-8")

    except Exception as e:
        status = getattr(e, "status_code", None) or 500
        raise HTTPException(status_code=status, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


# ---- Clips selection endpoint types & validators ----


class ReasonsModel(BaseModel):
    content_density: float
    hook: List[str]
    novelty_top_terms: List[str]
    coherence_notes: str
    penalties: List[str]


class SegmentModel(BaseModel):
    start: float
    end: float
    text: str


class ClipModel(BaseModel):
    rank: int
    start: float
    end: float
    duration: float
    score: float
    reasons: ReasonsModel
    preview_text: str
    segments: List[SegmentModel]


class ParamsModel(BaseModel):
    n_clips: int
    target_sec: float
    min_sec: float
    max_sec: float
    stride_sec: float
    min_gap_sec: float
    allow_promo: bool


class MetaModel(BaseModel):
    transcript_duration: float
    num_segments: int
    params: ParamsModel
    notes: List[str]


class ClipsSelectSchema(BaseModel):
    clips: List[ClipModel]
    meta: MetaModel


class TranscribeParams(BaseModel):
    input_path: str = Field(
        DEFAULT_SAMPLE_INPUT, description="Path to input media file"
    )
    model: str = Field(os.getenv("WHISPER_MODEL", "small"))
    language: Optional[str] = None
    compute_type: str = Field(os.getenv("WHISPER_COMPUTE_TYPE", "int8"))
    beam_size: int = Field(5, ge=1, le=10)
    vad: bool = True


class ProcessSampleRequest(BaseModel):
    transcribe: Optional[TranscribeParams] = None
    selection_config: Optional[dict] = None
    system: Optional[str] = None
    instructions: Optional[str] = Field(
        None,
        description="Optional user-specific instructions to guide selection",
    )
    model: str = Field(DEFAULT_MODEL, description="Model name")
    max_tokens: int = Field(2048, ge=256, le=8192)
    temperature: float = Field(0.0, ge=0.0, le=1.0)
    top_p: float = Field(1.0, ge=0.0, le=1.0)


class ProcessSampleResponse(BaseModel):
    input_path: str
    segments: List[SegmentModel]
    selection: ClipsSelectSchema


class UploadResponse(BaseModel):
    file_id: str
    filename: Optional[str]
    size: int
    local_copy: Optional[str] = None


class ClipFile(BaseModel):
    rank: int
    start: float
    end: float
    duration: float
    path: str


class ProcessRequest(BaseModel):
    file_id: Optional[str] = None
    segments: Optional[List[dict]] = None
    selection_config: Optional[dict] = None
    system: Optional[str] = None
    instructions: Optional[str] = Field(
        None,
        description="Optional user-specific instructions to guide selection",
    )
    model: str = Field(DEFAULT_MODEL, description="OpenAI model name")
    max_tokens: int = Field(4096, ge=512, le=8192)
    temperature: float = Field(0.0, ge=0.0, le=1.0)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    whisper_model: str = Field(os.getenv("WHISPER_MODEL", "small"))
    whisper_compute_type: str = Field(os.getenv("WHISPER_COMPUTE_TYPE", "int8"))
    whisper_language: Optional[str] = None
    whisper_beam_size: int = Field(5, ge=1, le=10)
    whisper_vad: bool = True


class ProcessResponse(BaseModel):
    job_id: str
    file_id: str
    input_path: str
    segments: List[SegmentModel]
    selection: ClipsSelectSchema
    clips: List[ClipFile]
    combined_video: Optional[str] = None
    candidate_dir: Optional[str] = None
    candidates: Optional[List[str]] = None
    final_video: Optional[str] = None


class CreateCandidatesRequest(BaseModel):
    video_path: str
    # Provide either selection (clips schema) or segments
    selection: Optional[ClipsSelectSchema] = None
    segments: Optional[List[SegmentModel]] = None
    output_dir: Optional[str] = None  # defaults to candidate_videos
    combine_output: bool = True
    words_data: Optional[List[Dict[str, Any]]] = None  # word-level timestamps for subtitle burn-in
    transition_titles: Optional[List[str]] = None  # AI-generated title cards


class CreateCandidatesResponse(BaseModel):
    candidate_dir: str
    candidates: List[str]
    combined_video: Optional[str] = None


class ClipsSelectRequest(BaseModel):
    # Supply either `payload` (arbitrary dict or list), or `segments` with optional `config`.
    payload: Optional[Union[dict, list]] = Field(
        None, description="Raw transcript payload to send to the model"
    )
    segments: Optional[List[dict]] = Field(
        None, description="Segments array; will be wrapped and sent to the model"
    )
    config: Optional[dict] = Field(None, description="Optional config if using segments")

    # Overrides
    instructions: Optional[str] = Field(
        None,
        description="Optional user-specific instructions to guide selection",
    )
    system: Optional[str] = None
    model: str = Field(DEFAULT_MODEL, description="GPT model name")
    max_tokens: int = Field(2048, ge=256, le=8192)
    temperature: float = Field(0.0, ge=0.0, le=1.0)
    top_p: float = Field(1.0, ge=0.0, le=1.0)


def _extract_text_from_response(resp) -> str:
    # Chat completion content (OpenAI / Gemini compatible)
    try:
        text = (resp.choices[0].message.content or "").strip()
        # Strip markdown code fences that Gemini may wrap around JSON
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()
        return text
    except Exception:
        return ""


def _validate_clips_output(text: str, *, min_gap_override: Optional[float] = None, repair: bool = True) -> ClipsSelectSchema:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Raw model response (first 2000 chars): {text[:2000]}")
        raise HTTPException(status_code=502, detail=f"Model did not return valid JSON: {e}")

    try:
        parsed = ClipsSelectSchema.model_validate(data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"JSON schema validation failed: {e}")

    # Additional logical validations
    try:
        # Determine min gap to enforce
        min_gap = (
            float(min_gap_override)
            if min_gap_override is not None
            else (parsed.meta.params.min_gap_sec if parsed.meta and parsed.meta.params else 5.0)
        )

        clips_sorted = sorted(parsed.clips, key=lambda c: (c.start, c.end))
        # Unique ranks
        ranks = [c.rank for c in parsed.clips]
        if len(ranks) != len(set(ranks)):
            raise ValueError("Duplicate clip ranks detected")

        # Non-overlap and min gap
        prev_end = None
        violations = []
        for c in clips_sorted:
            if c.start >= c.end:
                raise ValueError("Clip has non-positive duration")
            # Duration consistency within small tolerance
            if abs((c.end - c.start) - c.duration) > 1e-3:
                raise ValueError("Clip duration does not equal end-start")
            if prev_end is not None:
                if c.start < prev_end:
                    violations.append(("overlap", c))
                elif (c.start - prev_end) < (min_gap - 1e-6):
                    violations.append(("gap", c))
            prev_end = c.end

        # Score bounds
        for c in parsed.clips:
            if not (0.0 <= c.score <= 1.0):
                raise ValueError("Score outside [0,1]")
            if not (0.0 <= c.reasons.content_density <= 1.0):
                raise ValueError("content_density outside [0,1]")

        # If violations exist, optionally repair by dropping lower-priority clips
        if violations:
            if not repair:
                # Raise a combined error message
                kinds = sorted(set(k for k, _ in violations))
                raise ValueError(
                    f"Violations detected: {', '.join(kinds)} (min_gap={min_gap})"
                )

            # Greedy repair: prefer lower rank (1 is best). Keep as many as possible.
            # A clip conflicts if it overlaps or is within min_gap of any kept clip.
            def conflicts(a, b) -> bool:
                if (a.end > b.start) and (a.start < b.end):
                    return True  # overlap
                # Check gap both directions
                if a.start >= b.end:
                    return (a.start - b.end) < (min_gap - 1e-6)
                if b.start >= a.end:
                    return (b.start - a.end) < (min_gap - 1e-6)
                return False

            kept: List[ClipModel] = []
            for c in sorted(parsed.clips, key=lambda x: x.rank):
                if all(not conflicts(c, k) for k in kept):
                    kept.append(c)

            if not kept:
                raise ValueError("All clips conflicted; unable to repair selection")

            # Renumber ranks sequentially by original rank order of kept
            kept_sorted_by_rank = sorted(kept, key=lambda x: x.rank)
            for idx, c in enumerate(kept_sorted_by_rank, start=1):
                c.rank = idx

            parsed = deepcopy(parsed)
            parsed.clips = kept_sorted_by_rank
            # Append a note
            try:
                if parsed.meta and isinstance(parsed.meta.notes, list):
                    parsed.meta.notes.append(
                        f"server_repair: adjusted selection to satisfy min_gap={min_gap}"
                    )
            except Exception:
                pass
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=f"Validation error: {ve}")

    return parsed


@app.post("/clips/select")
def clips_select(req: ClipsSelectRequest):
    # Build input payload
    if req.payload is not None:
        input_obj: Any = req.payload
    elif req.segments is not None:
        input_obj = {"segments": req.segments}
        if req.config is not None:
            input_obj["config"] = req.config
    else:
        raise HTTPException(status_code=400, detail="Provide `payload` or `segments`.")

    # Prepare request to model
    client = _get_client()
    system_text = _resolve_system_prompt(req.system)
    user_json = json.dumps(input_obj, ensure_ascii=False)

    try:
        messages = []
        if system_text:
            messages.append({"role": "system", "content": system_text})
        if req.instructions and req.instructions.strip():
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Additional user instructions to apply when selecting clips. "
                        "Do not output anything except the final JSON described in the system prompt.\n\n"
                        f"Instructions:\n{req.instructions}"
                    ),
                }
            )
        messages.append({"role": "user", "content": user_json})
        resp = client.chat.completions.create(
            model=req.model,
            messages=messages,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            top_p=req.top_p,
        )
        text = _extract_text_from_response(resp)
        # If request provides a min_gap_sec, use it to validate; otherwise rely on model meta or default
        min_gap_override = None
        try:
            if isinstance(req.config, dict) and "min_gap_sec" in req.config:
                min_gap_override = float(req.config["min_gap_sec"])  # type: ignore
        except Exception:
            pass
        parsed = _validate_clips_output(text, min_gap_override=min_gap_override, repair=True)
        # Return repaired/validated JSON
        return PlainTextResponse(parsed.model_dump_json(indent=None), media_type="application/json")
    except Exception as e:
        status = getattr(e, "status_code", None) or 500
        raise HTTPException(status_code=status, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.post("/process/sample", response_model=ProcessSampleResponse)
def process_sample(req: ProcessSampleRequest):
    """Transcribe the sample media (or provided input) and select clips via GPT.

    Returns both the raw segments and the model's clip selection JSON.
    """
    # Transcription params
    tp = req.transcribe or TranscribeParams()
    segments = _transcribe_media(
        input_path=tp.input_path,
        model_size=tp.model,
        language=tp.language,
        compute_type=tp.compute_type,
        beam_size=tp.beam_size,
        vad=tp.vad,
    )

    # Build payload for selection
    payload: dict = {"segments": segments}
    if req.selection_config:
        payload["config"] = req.selection_config

    # Call GPT
    client = _get_client()
    system_text = _resolve_system_prompt(req.system)
    user_json = json.dumps(payload, ensure_ascii=False)

    try:
        messages = []
        if system_text:
            messages.append({"role": "system", "content": system_text})
        if req.instructions and req.instructions.strip():
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Additional user instructions to apply when selecting clips. "
                        "Do not output anything except the final JSON described in the system prompt.\n\n"
                        f"Instructions:\n{req.instructions}"
                    ),
                }
            )
        messages.append({"role": "user", "content": user_json})
        resp = client.chat.completions.create(
            model=req.model,
            messages=messages,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            top_p=req.top_p,
        )
        text = _extract_text_from_response(resp)
        min_gap_override = None
        try:
            if isinstance(req.selection_config, dict) and "min_gap_sec" in req.selection_config:
                min_gap_override = float(req.selection_config["min_gap_sec"])  # type: ignore
        except Exception:
            pass
        parsed = _validate_clips_output(text, min_gap_override=min_gap_override, repair=True)
        return ProcessSampleResponse(
            input_path=tp.input_path,
            segments=[SegmentModel(**s) for s in segments],
            selection=parsed,
        )
    except Exception as e:
        status = getattr(e, "status_code", None) or 500
        raise HTTPException(status_code=status, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


# ---------------- New Organized Endpoints ----------------


@app.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    # Legacy extraction params (trigger immediate transcription + outputs)
    model: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    compute_type: str = Query("int8"),
    beam_size: int = Query(5),
    vad: bool = Query(False),
    # User-provided instructions (either in form field or query)
    instructions: Optional[str] = Form(None),
    instructions_q: Optional[str] = Query(None),
):
    """Upload a file. Compatibility modes:

    - If legacy params like `model` are provided, perform immediate caption extraction
      and return job_id + output file links (legacy UI contract).
    - Otherwise, just store and return a `file_id` for later `/process`.
    """
    try:
        meta = _save_upload(file)
        # Legacy flow: perform extraction immediately when a model is specified
        if model is not None:
            if _extract_write_outputs is None:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Legacy extraction not available: missing extract_captions."
                    ),
                )
            # Create a job directory under outputs and run the writer
            job_id = str(uuid.uuid4())
            job_dir = os.path.join(OUTPUT_DIR, job_id)
            os.makedirs(job_dir, exist_ok=True)

            # Normalize compute_type (avoid float16 on Windows) and attempt extraction
            ct = _normalize_compute_type(compute_type)
            _force_cpu_for_ct2()
            try:
                logger.info(f"Transcription input: {meta.get('local_copy') or meta['path']}")
                eff_model = os.getenv('WHISPER_MODEL', 'small')
                logger.info(f"Transcription mode: faster-whisper via extra_captions.py (model={eff_model}, compute_type={ct})")
                _extract_write_outputs(
                    input_path=meta.get("local_copy") or meta["path"],
                    outdir=job_dir,
                    model=eff_model,
                    language=language,
                    compute_type=ct,
                    beam_size=int(beam_size),
                    vad=bool(vad),
                )
            except Exception as e:
                # Retry once with CPU-safe compute type
                if ct != "int8":
                    try:
                        logger.info("Local extraction failed; retrying via extra_captions.py with compute_type=int8")
                        _extract_write_outputs(
                            input_path=meta.get("local_copy") or meta["path"],
                            outdir=job_dir,
                            model=os.getenv("WHISPER_MODEL", "small"),
                            language=language,
                            compute_type="int8",
                            beam_size=int(beam_size),
                            vad=bool(vad),
                        )
                    except Exception as e2:
                        # Fallback to OpenAI Whisper API if local extraction fails
                        try:
                            logger.info("Extraction retry failed; falling back to OpenAI Whisper API (legacy writer)")
                            _openai_whisper_fallback_write_outputs(meta["path"], job_dir)
                        except Exception as fe:
                            raise HTTPException(status_code=500, detail=f"Extraction failed: {e2}; Fallback failed: {fe}")
                else:
                    # Fallback to OpenAI Whisper API if local extraction fails
                    try:
                        logger.info("Extraction failed; falling back to OpenAI Whisper API (legacy writer)")
                        _openai_whisper_fallback_write_outputs(meta["path"], job_dir)
                    except Exception as fe:
                        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}; Fallback failed: {fe}")

            # Legacy response shape
            output_files = {
                "transcript_txt": f"/download/{job_id}/transcript.txt",
                "segments_json": f"/download/{job_id}/segments.json",
                "words_json": f"/download/{job_id}/words.json",
                "transcript_srt": f"/download/{job_id}/transcript.srt",
                "transcript_vtt": f"/download/{job_id}/transcript.vtt",
            }
            resp_payload = {
                "success": True,
                "message": "Caption extraction completed successfully",
                "job_id": job_id,
                "output_files": output_files,
                "local_copy": meta.get("local_copy"),
            }

            # Auto-run candidate creation and final combination if splicer is available
            try:
                segments_json_path = os.path.join(job_dir, "segments.json")
                with open(segments_json_path, "r", encoding="utf-8") as f:
                    segs = json.load(f)

                # Build selection via Gemini/OpenAI using the same prompt/validator as /process
                logger.info("Selecting clips via AI for candidate generation")
                client = _get_client()
                system_text = _resolve_system_prompt(None)
                user_json = json.dumps({"segments": segs}, ensure_ascii=False)
                messages = []
                if system_text:
                    messages.append({"role": "system", "content": system_text})
                eff_instructions = instructions or instructions_q
                if eff_instructions and eff_instructions.strip():
                    messages.append({
                        "role": "user",
                        "content": (
                            "Additional user instructions to apply when selecting clips. "
                            "Do not output anything except the final JSON described in the system prompt.\n\n"
                            f"Instructions:\n{eff_instructions.strip()}"
                        ),
                    })
                messages.append({"role": "user", "content": user_json})

                # Use native Gemini SDK if available, otherwise OpenAI
                if genai is not None and isinstance(client, genai.Client):
                    text = _gemini_chat(client, messages, DEFAULT_MODEL)
                else:
                    resp = client.chat.completions.create(
                        model=DEFAULT_MODEL,
                        messages=messages,
                        max_tokens=8192,
                        temperature=0.0,
                        top_p=1.0,
                    )
                    text = _extract_text_from_response(resp)
                selection = _validate_clips_output(text, repair=True)
                with open(os.path.join(job_dir, "selection.json"), "w", encoding="utf-8") as fsel:
                    fsel.write(selection.model_dump_json(indent=2))

                # Load word-level timestamps for subtitle burn-in
                words_data = []
                words_json_path = os.path.join(job_dir, "words.json")
                if os.path.exists(words_json_path):
                    with open(words_json_path, "r", encoding="utf-8") as fw:
                        words_data = json.load(fw)

                # Generate transition titles via Gemini
                transition_titles = []
                try:
                    sorted_clips = sorted(selection.clips, key=lambda c: c.start)
                    clip_summaries = [f"Clip {i+1}: \"{c.preview_text[:120]}\"" for i, c in enumerate(sorted_clips)]
                    title_prompt = (
                        "For each video clip below, generate a short dramatic title (3-8 words) "
                        "that would appear as a title card before the clip in a highlight reel. "
                        "Make them punchy and engaging. Return ONLY a JSON array of strings, one per clip.\n\n"
                        + "\n".join(clip_summaries)
                    )
                    if genai is not None and isinstance(client, genai.Client):
                        title_text = _gemini_chat(client, [{"role": "user", "content": title_prompt}], DEFAULT_MODEL, max_tokens=1024)
                    else:
                        title_resp = client.chat.completions.create(
                            model=DEFAULT_MODEL,
                            messages=[{"role": "user", "content": title_prompt}],
                            max_tokens=1024, temperature=0.7,
                        )
                        title_text = _extract_text_from_response(title_resp)
                    transition_titles = json.loads(title_text)
                    logger.info(f"Generated {len(transition_titles)} transition titles")
                except Exception as te:
                    logger.warning(f"Transition title generation failed: {te}")

                logger.info("Starting candidate generation via internal create-candidates endpoint")
                cc_req = CreateCandidatesRequest(
                    video_path=meta.get("local_copy") or meta["path"],
                    selection=selection,
                    output_dir=CANDIDATE_VIDEOS_DIR,
                    combine_output=False,
                    words_data=words_data,
                    transition_titles=transition_titles,
                )
                cc_resp = create_candidate_videos(cc_req)
                resp_payload["candidates"] = cc_resp.candidates
                # Promote the chronological candidate into output_videos
                final_path = _promote_chronological_candidate_to_output(
                    meta.get("local_copy") or meta["path"], CANDIDATE_VIDEOS_DIR, cc_resp.candidates
                )
                if final_path:
                    resp_payload["final_video"] = final_path
            except Exception as ce:
                logger.warning(f"Candidate generation skipped due to error: {ce}")

            return JSONResponse(resp_payload)

        # New flow: return file_id and local_copy path for convenience
        return JSONResponse(
            {
                "file_id": meta["file_id"],
                "filename": meta["filename"],
                "size": meta["size"],
                "local_copy": meta.get("local_copy"),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@app.post("/process", response_model=ProcessResponse)
def process_pipeline(req: ProcessRequest):
    _ensure_dirs()
    segments: List[dict]
    input_path: Optional[str] = None

    # Allow client-supplied segments to skip server transcription
    if req.segments:
        if not isinstance(req.segments, list) or not req.segments:
            raise HTTPException(status_code=400, detail="`segments` must be a non-empty array")
        segments = req.segments  # type: ignore
    else:
        # Resolve upload path from file_id
        if not req.file_id:
            raise HTTPException(status_code=400, detail="Provide `segments` or `file_id`.")

        candidates = list(Path(UPLOAD_DIR).glob(f"{req.file_id}.*"))
        if not candidates:
            raise HTTPException(status_code=404, detail=f"file_id not found: {req.file_id}")
        input_path = str(candidates[0])

        # 1) Transcribe (if allowed)
        if not ALLOW_SERVER_TRANSCRIPTION:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Server-side transcription is disabled. Provide `segments` in the request body "
                    "(precomputed locally via faster-whisper)."
                ),
            )

        segments = _transcribe_media(
            input_path=input_path,
            model_size=req.whisper_model,
            language=req.whisper_language,
            compute_type=req.whisper_compute_type,
            beam_size=req.whisper_beam_size,
            vad=req.whisper_vad,
        )

    # 2) Generate candidate videos directly from transcribed segments
    cc_candidates: Optional[List[str]] = None
    cc_final: Optional[str] = None
    try:
        if input_path:
            logger.info("Starting candidate generation from selected clips (process pipeline)")
            # We'll build selection after the OpenAI selection step below.
    except Exception as ce:
        logger.warning(f"create-candidates precheck failed: {ce}")

    # 3) Select clips via OpenAI
    client = _get_client()
    system_text = _resolve_system_prompt(req.system)
    payload = {"segments": segments}
    if req.selection_config:
        payload["config"] = req.selection_config
    user_json = json.dumps(payload, ensure_ascii=False)

    messages = []
    if system_text:
        messages.append({"role": "system", "content": system_text})
    if req.instructions and req.instructions.strip():
        messages.append(
            {
                "role": "user",
                "content": (
                    "Additional user instructions to apply when selecting clips. "
                    "Do not output anything except the final JSON described in the system prompt.\n\n"
                    f"Instructions:\n{req.instructions}"
                ),
            }
        )
    messages.append({"role": "user", "content": user_json})

    try:
        resp = client.chat.completions.create(
            model=req.model,
            messages=messages,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            top_p=req.top_p,
        )
        text = _extract_text_from_response(resp)
        min_gap_override = None
        try:
            if isinstance(req.selection_config, dict) and "min_gap_sec" in req.selection_config:
                min_gap_override = float(req.selection_config["min_gap_sec"])  # type: ignore
        except Exception:
            pass
        selection = _validate_clips_output(text, min_gap_override=min_gap_override, repair=True)
    except Exception as e:
        status = getattr(e, "status_code", None) or 500
        raise HTTPException(status_code=status, detail=f"Model error: {e}")

    # 3b) Now that we have selection, create candidate videos prioritized via VideoSplicer
    try:
        if input_path:
            cc_req = CreateCandidatesRequest(
                video_path=input_path,
                selection=selection,
                output_dir=CANDIDATE_VIDEOS_DIR,
                combine_output=False,
            )
            cc_resp = create_candidate_videos(cc_req)
            cc_candidates = cc_resp.candidates
            cc_final = _promote_chronological_candidate_to_output(input_path, CANDIDATE_VIDEOS_DIR, cc_candidates)
    except Exception as ce:
        logger.warning(f"create-candidates failed in process pipeline: {ce}")

    # 4) Render clips (optional; keeps current behavior for selection clips)
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    # Save artifacts
    with open(os.path.join(job_dir, "segments.json"), "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)
    with open(os.path.join(job_dir, "selection.json"), "w", encoding="utf-8") as f:
        f.write(selection.model_dump_json(indent=2))

    clips_out: List[ClipFile] = []
    for c in selection.clips:
        name = f"clip_rank{c.rank}_{c.start:.3f}-{c.end:.3f}.mp4"
        out_path = os.path.join(job_dir, name)
        try:
            # If no input media is available (segments-only case), skip rendering
            if input_path:
                _ffmpeg_extract_clip(input_path, out_path, c.start, c.end)
            clips_out.append(
                ClipFile(
                    rank=c.rank,
                    start=c.start,
                    end=c.end,
                    duration=c.duration,
                    path=f"{job_id}/{name}" if input_path else "",
                )
            )
        except Exception as e:
            # Skip rendering failures but continue
            continue

    # Prefer promoted segment candidate; do not combine all by default
    combined_path = None

    return ProcessResponse(
        job_id=job_id,
        file_id=req.file_id,
        input_path=input_path,
        segments=[SegmentModel(**s) for s in segments],
        selection=selection,
        clips=sorted(clips_out, key=lambda x: x.rank),
        combined_video=combined_path,
        candidate_dir=CANDIDATE_VIDEOS_DIR if cc_candidates else None,
        candidates=cc_candidates,
        final_video=cc_final,
    )


@app.get("/download")
def download_clip(job_id: str, filename: str):
    """Fetch a rendered clip file.

    Params:
    - job_id: UUID returned by /process
    - filename: file name from the `clips[].path` (only the basename)
    """
    safe_name = os.path.basename(filename)
    path = os.path.join(OUTPUT_DIR, job_id, safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Clip not found")
    return FileResponse(path, media_type="video/mp4", filename=safe_name)


# Legacy path-style download route for UI compatibility
@app.get("/download/{job_id}/{filename}")
def download_legacy(job_id: str, filename: str):
    safe_name = os.path.basename(filename)
    path = os.path.join(OUTPUT_DIR, job_id, safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    # Guess a content type by extension; default to octet-stream
    media = "application/octet-stream"
    if safe_name.lower().endswith(".mp4"):
        media = "video/mp4"
    elif safe_name.lower().endswith(".srt"):
        media = "text/plain"
    elif safe_name.lower().endswith(".vtt"):
        media = "text/vtt"
    elif safe_name.lower().endswith(".json"):
        media = "application/json"
    return FileResponse(path, media_type=media, filename=safe_name)


@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    """Legacy job status endpoint compatible with the existing frontend.

    Lists available files for a job directory created by the legacy upload flow.
    """
    job_dir = os.path.join(OUTPUT_DIR, job_id)
    if not os.path.isdir(job_dir):
        raise HTTPException(status_code=404, detail="Job not found")
    files = []
    try:
        for name in os.listdir(job_dir):
            path = os.path.join(job_dir, name)
            if os.path.isfile(path):
                files.append(
                    {
                        "filename": name,
                        "download_url": f"/download/{job_id}/{name}",
                        "size": os.path.getsize(path),
                    }
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading job files: {e}")

    return {"job_id": job_id, "status": "completed", "files": files}


@app.post("/create-candidates", response_model=CreateCandidatesResponse)
def create_candidate_videos(req: CreateCandidatesRequest):
    """Create candidate videos given a video path and either selection clips or raw segments.

    - Writes an intermediate selection JSON compatible with VideoSplicer
    - Generates candidate videos into `candidate_videos/` (or overridden output_dir)
    - Concatenates all candidate videos into one file under `output_videos/`
    """
    VS = _get_videosplicer()
    if VS is None:
        raise HTTPException(status_code=500, detail="VideoSplicer not available")

    video_path = req.video_path
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail=f"Input video not found: {video_path}")

    # Build selection payload
    if req.selection is not None:
        selection_payload = req.selection.model_dump()
    elif req.segments is not None and len(req.segments) > 0:
        clips = []
        for i, seg in enumerate(req.segments):
            start = float(seg.start)
            end = float(seg.end)
            text = seg.text
            clips.append({
                "rank": i + 1,
                "start": start,
                "end": end,
                "duration": max(0.0, end - start),
                "score": 0.50,
                "reasons": {
                    "content_density": 0.50,
                    "hook": [],
                    "novelty_top_terms": [],
                    "coherence_notes": "",
                    "penalties": [],
                },
                "preview_text": text[:160],
                "segments": [
                    {"start": start, "end": end, "text": text}
                ],
            })
        selection_payload = {"clips": clips, "meta": {}}
    else:
        raise HTTPException(status_code=400, detail="Provide either `selection` or non-empty `segments`.")

    # Prepare directories and temp file
    out_dir = req.output_dir or CANDIDATE_VIDEOS_DIR
    os.makedirs(out_dir, exist_ok=True)
    temp_json = os.path.join(tempfile.gettempdir(), f"candidates_{uuid.uuid4().hex}.json")
    with open(temp_json, "w", encoding="utf-8") as f:
        json.dump(selection_payload, f, ensure_ascii=False, indent=2)

    # Run splicer
    try:
        _ensure_ffmpeg_available()
        splicer = VS(video_path, temp_json, out_dir,
                     words_data=req.words_data or [],
                     transition_titles=req.transition_titles or [])
        candidate_paths = splicer.create_all_candidates() or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Splicer error: {e}")

    combined_path = None
    if req.combine_output and candidate_paths:
        os.makedirs(FINAL_VIDEOS_DIR, exist_ok=True)
        combined_path = os.path.join(FINAL_VIDEOS_DIR, f"combined_candidates_{uuid.uuid4().hex}.mp4")
        concat_list = os.path.join(tempfile.gettempdir(), f"concat_{uuid.uuid4().hex}.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for p in candidate_paths:
                f.write(f"file '{os.path.abspath(p)}'\n")
        cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", "-y", combined_path]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except Exception as e:
            logger.warning(f"Combine candidates failed: {e}")
            combined_path = None

    return CreateCandidatesResponse(candidate_dir=out_dir, candidates=candidate_paths, combined_video=combined_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
