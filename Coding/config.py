"""
config.py  –  All tunable settings for the ANPR system
Edit this file before running main.py
"""

# ─── Camera ───────────────────────────────────────────────────────────────────
CAMERA_SOURCE      = 0          # 0 = default laptop webcam; RTSP URL also accepted
CAMERA_ID          = "laptop_cam"
FRAME_WIDTH        = 1280
FRAME_HEIGHT       = 720
CAPTURE_FPS        = 30
PROCESS_EVERY_N_FRAMES = 5      # Run OCR every N frames (performance vs latency)

# ─── OCR ──────────────────────────────────────────────────────────────────────
OCR_CONFIDENCE_THRESHOLD = 0.70  # Ignore detections below this
OCR_LANGUAGES            = ["en"]
USE_GPU                  = False  # Set True if CUDA is available

# ─── Plate format (regex) ─────────────────────────────────────────────────────
# India: TN09AB1234  |  change for your country
PLATE_REGEX = r"^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$"

# ─── Duplicate suppression ────────────────────────────────────────────────────
DUPLICATE_COOLDOWN_SECONDS = 30  # Ignore same plate within this window

# ─── Firebase ─────────────────────────────────────────────────────────────────
FIREBASE_SERVICE_ACCOUNT = "serviceAccountKey.json"  # Download from Firebase console
FIREBASE_DATABASE_URL    = "https://your-project-id.firebaseio.com"
FIREBASE_STORAGE_BUCKET  = "your-project-id.appspot.com"

# ─── Telegram ─────────────────────────────────────────────────────────────────
# Create bot via @BotFather, get chat ID from @userinfobot
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID   = "YOUR_CHAT_ID_HERE"

# ─── Bounding box / preprocessing ────────────────────────────────────────────
MIN_PLATE_AREA    = 500     # px²  – smaller contours ignored
MAX_PLATE_AREA    = 50000   # px²  – larger contours ignored
MIN_ASPECT_RATIO  = 2.0     # width / height
MAX_ASPECT_RATIO  = 5.0
CANNY_THRESHOLD1  = 100
CANNY_THRESHOLD2  = 200
GAUSSIAN_KERNEL   = (5, 5)
