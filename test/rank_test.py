import requests
import subprocess
import os
import json

BASE = "http://localhost:8000"

# Video and subtitle file paths
INPUT_VIDEO = "input_videos/input1.mp4"
SUBTITLE_FILE = "captions_out/transcript.srt"
OUTPUT_DIR = "outputs"

segments = [
     {
    "start": 6.499999999999997,
    "end": 13.76,
    "text": "Well, there you go! It only took like eight years. Oh my God!"
  },
  {
    "start": 21.080000000000002,
    "end": 22.48,
    "text": "Okay!"
  },
  {
    "start": 111.32000000000001,
    "end": 114.44,
    "text": "Three, two, one."
  },
  {
    "start": 123.76,
    "end": 124.82,
    "text": "Oh man!"
  },
  {
    "start": 124.82,
    "end": 125.2,
    "text": "Yeah!"
  },
  {
    "start": 132.78,
    "end": 135.5,
    "text": "Okay, that was cleaner than the last one."
  },
  {
    "start": 139.72,
    "end": 143.46,
    "text": "Where are my legs? Why aren't the legs out?"
  },
  {
    "start": 143.46,
    "end": 143.88,
    "text": "Ah!"
  },
  {
    "start": 202.04,
    "end": 203.44,
    "text": "Ah!"
  },
  {
    "start": 210.10000000000002,
    "end": 217.1,
    "text": "Hey, my name is Joe Barnard. I built this rocket, and I have been trying to do what you just saw for seven years."
  },
  {
    "start": 217.36,
    "end": 222.36,
    "text": "I started this project back in the fall of 2015 with the goal to propulsively land a model rocket,"
  },
  {
    "start": 222.7,
    "end": 226.46,
    "text": "and not because it's revolutionary or game-changing for model rocketry,"
  },
  {
    "start": 226.74,
    "end": 230.24,
    "text": "but because it's a really cool project and I knew I would learn a lot."
  },
  {
    "start": 230.24,
    "end": 235.02,
    "text": "And I did learn a lot. You can scroll back through the uploads on this channel and see for yourself"
  },
  {
    "start": 235.02,
    "end": 241.94,
    "text": "how I started by failing and failing and failing and then burning out and failing more and burning out again."
  },
  {
    "start": 242.32,
    "end": 247.9,
    "text": "But slowly, over time, you can see the reliability of these flights just inch up, tick by tick."
  },
  {
    "start": 248.1,
    "end": 251.4,
    "text": "With the original goal accomplished here, it's time to set some new goals."
  },
  {
    "start": 251.56,
    "end": 257.8,
    "text": "And before I do that, I want to say thank you so much to everyone who has supported over these last seven years."
  },
  {
    "start": 257.8,
    "end": 263.14,
    "text": "Whether that means watching these videos, supporting on Patreon, just giving a video a like."
  },
  {
    "start": 263.66,
    "end": 268.94,
    "text": "Any type of support that you have provided over these last years means the world to me."
  },
  {
    "start": 269.2,
    "end": 272.8,
    "text": "And it's crazy that I get to do this and it's somehow a job."
  },
  {
    "start": 273.16,
    "end": 279.34,
    "text": "So thank you so much to everyone who has contributed in any way. It means the world to me."
  },
  {
    "start": 279.42,
    "end": 282.3,
    "text": "And before we wrap it up here, I want to talk about what's coming next."
  },
  {
    "start": 282.52,
    "end": 284.04,
    "text": "The first is more scout flights."
  },
  {
    "start": 284.04,
    "end": 288.34,
    "text": "I want to get at least one or two more flights in to see if we can get that landing a little less sporty."
  },
  {
    "start": 288.84,
    "end": 291.1,
    "text": "This one was a little bit more slam than hover."
  },
  {
    "start": 291.38,
    "end": 297.3,
    "text": "If you want to watch those flights live as they happen, if you want the raw flight footage and data and access to the Discord"
  },
  {
    "start": 297.3,
    "end": 301.5,
    "text": "and all sorts of other perks, you can join the BPS Patreon linked down below."
  },
  {
    "start": 301.74,
    "end": 305.04,
    "text": "Supporting on Patreon helps make projects like these actually possible."
  },
  {
    "start": 305.98,
    "end": 307.1,
    "text": "This thing is a money pit."
  },
  {
    "start": 307.34,
    "end": 312.76,
    "text": "And so as a thank you to everyone who already supports on Patreon, you flew on this flight."
  },
  {
    "start": 312.76,
    "end": 317.58,
    "text": "I flew every patron name on this flight. So if you support, you were part of this."
  },
  {
    "start": 317.76,
    "end": 320.78,
    "text": "And as for what's coming up next on this channel, we have three big things."
  },
  {
    "start": 320.94,
    "end": 326.24,
    "text": "The first is a Starship Super Heavy model. This thing is huge. It's like nine feet tall."
  },
  {
    "start": 326.66,
    "end": 330.14,
    "text": "We're going to launch it. We're going to belly flop it. And we'll see about the landing."
  },
  {
    "start": 330.42,
    "end": 334.74,
    "text": "Project number two is the meat rocket. I'm not going to tell you what the meat rocket is."
  },
  {
    "start": 335.06,
    "end": 338.0,
    "text": "I'm not even going to give you a hint. You're just going to have to find out. It's crazy."
  },
  {
    "start": 338.0,
    "end": 342.24,
    "text": "And project number three, which is the new main goal for me is a space shop."
  },
  {
    "start": 342.34,
    "end": 346.94,
    "text": "That's a rocket that goes over 100 kilometers. I've been quietly working on this project in the background."
  },
  {
    "start": 347.22,
    "end": 352.7,
    "text": "It's still a year or two away and, you know, a couple of dollar signs away, but we're getting there."
  },
  {
    "start": 353.1,
    "end": 356.66,
    "text": "It's a really fun goal. It's a really challenging thing, just like landing it."
  },
  {
    "start": 356.78,
    "end": 359.84,
    "text": "I'm excited to see how far we can get. And one more thing before I go."
  },
  {
    "start": 360.02,
    "end": 366.22,
    "text": "If you want to be a BPS intern, you can be a part of the only aerospace company made up entirely of interns."
  },
  {
    "start": 366.22,
    "end": 368.92,
    "text": "You can do that with the link in the description down below."
  },
  {
    "start": 369.08,
    "end": 374.34,
    "text": "Anyway, thank you for watching. Thank you all for such generosity and support over these last few years."
  },
  {
    "start": 374.72,
    "end": 378.44,
    "text": "And I'm really excited to see what comes next. I'm Joe Barnard."
  },
  {
    "start": 378.82,
    "end": 381.34,
    "text": "May your skies be blue and your winds be low."
  },
  {
    "start": 420.86000000000007,
    "end": 423.66,
    "text": "Thank you."
  }
]

def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def extract_clip_with_captions(start_time, end_time, output_name, rank):
    """Extract a video clip with captions overlaid"""
    
    # Check if FFmpeg is available
    if not check_ffmpeg():
        print("❌ FFmpeg not found! Please install it with: brew install ffmpeg")
        return None
    
    # Check if input files exist
    if not os.path.exists(INPUT_VIDEO):
        print(f"❌ Input video not found: {INPUT_VIDEO}")
        return None
    
    if not os.path.exists(SUBTITLE_FILE):
        print(f"❌ Subtitle file not found: {SUBTITLE_FILE}")
        return None
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    output_path = os.path.join(OUTPUT_DIR, f"clip_rank{rank}_{output_name}.mp4")
    
    print(f"🎬 Extracting clip {rank}: {start_time:.1f}s - {end_time:.1f}s")
    print(f"   Input: {INPUT_VIDEO}")
    print(f"   Subtitles: {SUBTITLE_FILE}")
    print(f"   Output: {output_path}")
    
    # FFmpeg command with styled subtitles
    cmd = [
        "ffmpeg", "-y",  # -y to overwrite output files
        "-i", INPUT_VIDEO,
        "-ss", str(start_time),
        "-to", str(end_time),
        "-vf", f"subtitles={SUBTITLE_FILE}:force_style='FontName=Helvetica,FontSize=24,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2,Alignment=2'",
        "-c:a", "copy",
        output_path
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Created: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error creating {output_name}:")
        print(f"   Command: {' '.join(cmd)}")
        print(f"   Error: {e.stderr}")
        return None

def process_clips_with_captions(selection):
    """Process all AI-selected clips and extract them with captions"""
    
    print(f"\n🎬 Processing {len(selection['clips'])} AI-selected clips with captions...")
    
    # Extract each clip with captions
    for clip in selection['clips']:
        start = clip['start']
        end = clip['end']
        rank = clip['rank']
        score = clip['score']
        duration = clip['duration']
        
        print(f"\n📹 Clip {rank} (Score: {score:.2f})")
        print(f"   Time: {start:.1f}s - {end:.1f}s ({duration:.1f}s)")
        print(f"   Preview: {clip['preview_text'][:100]}...")
        
        output_name = f"{start:.1f}-{end:.1f}s"
        extract_clip_with_captions(start, end, output_name, rank)
    
    print(f"\n🎉 All clips processed! Check the '{OUTPUT_DIR}' directory.")

body = {
    "segments": segments,
    "config": {
        "n_clips": 3,
        "target_sec": 25.0,
        "min_sec": 18.0,
        "max_sec": 35.0,
        "stride_sec": 8.0,
        "min_gap_sec": 6.0,
        "allow_promo": False
    },
    "instructions": "Focus on sections with strong hooks and concrete tips; avoid promos/filler.",
    "model": "gpt-4o-mini",
    "max_tokens": 2048,
    "temperature": 0.0
}

# Get AI clip selection
print("🤖 Getting AI clip selection...")
r = requests.post(f"{BASE}/clips/select", json=body)
r.raise_for_status()
selection = r.json()

print(f"📊 Found {len(selection['clips'])} clips")
print("\n" + "="*50)
print("AI SELECTED CLIPS:")
print("="*50)

for i, clip in enumerate(selection["clips"], 1):
    print(f"\n🎯 CLIP {i} (Score: {clip['score']:.2f})")
    print(f"   Time: {clip['start']:.1f}s - {clip['end']:.1f}s ({clip['duration']:.1f}s)")
    print(f"   Preview: {clip['preview_text'][:150]}...")
    print(f"   Reasons: {clip['reasons']['coherence_notes']}")

print("\n" + "="*50)

# Process clips with captions
process_clips_with_captions(selection)
