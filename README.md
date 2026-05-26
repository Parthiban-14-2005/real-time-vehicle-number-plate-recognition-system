# 🚗 Real-Time Vehicle Number Plate Recognition System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![Firebase](https://img.shields.io/badge/Firebase-Realtime_DB-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)
![Telegram](https://img.shields.io/badge/Telegram-Bot_API-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)
![EasyOCR](https://img.shields.io/badge/EasyOCR-1.7-FF6F00?style=for-the-badge)

**Detect · Recognise · Alert — in under 2 seconds**

</div>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Configuration](#-configuration)
- [Firebase Setup](#-firebase-setup)
- [Telegram Bot Setup](#-telegram-bot-setup)
- [How It Works](#-how-it-works)
- [Results](#-results)
- [Bot Commands](#-bot-commands)
- [Team](#-team)
- [License](#-license)

---

## 📖 Overview

A **real-time Automatic Number Plate Recognition (ANPR)** system that uses a standard laptop webcam to detect and read Indian vehicle registration plates. Every detection is instantly:

- 💾 Stored in **Firebase Realtime Database** with a cropped plate image
- 📲 Sent as a **Telegram alert** with photo, confidence score, and timestamp
- ⚠️ Flagged with a priority alert if the plate is on the **watchlist**

No dedicated hardware required — just your laptop camera.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📷 Laptop Webcam Input | Works with any built-in or USB webcam via `cv2.VideoCapture(0)` |
| 🔍 Adaptive Preprocessing | Bilateral filter + Canny edges for all lighting conditions |
| ✂️ Perspective Correction | 4-point warp to rectify angled plate regions |
| 🔤 Deep Learning OCR | EasyOCR with character allowlist for high accuracy |
| ☁️ Cloud Storage | Plate crop images uploaded to Firebase Storage |
| 🔔 Instant Telegram Alerts | Photo + metadata sent in < 2 seconds |
| 🚫 Duplicate Suppression | 30-second cooldown per plate to prevent alert floods |
| ⚠️ Watchlist Matching | Priority alerts for pre-registered plates |
| 🌐 Offline Mode | System continues working if Firebase is unreachable |
| 🧵 Non-blocking Threads | Firebase and Telegram run in daemon threads — camera never pauses |

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          LAPTOP WEBCAM                              │
│                       cv2.VideoCapture(0)                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │ Frame (every 5th)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     OpenCV PIPELINE (detector.py)                   │
│                                                                     │
│  Grayscale → Bilateral Filter → Canny Edges → Contour Extraction   │
│         → Aspect Ratio Filter → Perspective Warp → EasyOCR         │
│                          ↓ MSER Fallback                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │ (plate_text, confidence, roi, bbox)
                             ▼
              ┌──────────────────────────┐
              │   Duplicate Guard (30s)  │
              └──────────┬───────────────┘
                         │ New plate only
            ┌────────────┴─────────────┐
            ▼                          ▼
┌────────────────────┐      ┌──────────────────────┐
│  Firebase Client   │      │    Telegram Bot       │
│  (daemon thread)   │      │   (daemon thread)     │
│                    │      │                       │
│ • Save to RTDB     │      │ • Send plate photo    │
│ • Upload to        │      │ • Caption with conf,  │
│   Cloud Storage    │      │   time, camera ID     │
│ • Check watchlist  │      │ • ⚠️ Priority flag    │
└────────────────────┘      └──────────────────────┘
```

---

## 🛠 Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.10 | Core language |
| OpenCV | 4.8.1 | Image capture, preprocessing, contour detection |
| EasyOCR | 1.7.0 | Deep learning OCR engine |
| firebase-admin | 6.3.0 | Realtime DB + Cloud Storage SDK |
| Telegram Bot API | Latest | Instant alerts + remote commands |
| NumPy | 1.24+ | Perspective transform calculations |

---

## 📁 Project Structure

```
anpr-system/
│
├── main.py               # Entry point — webcam loop, frame dispatch, live preview
├── detector.py           # OpenCV pipeline + EasyOCR + MSER fallback
├── firebase_client.py    # Firebase Realtime DB, Cloud Storage, watchlist, dedup
├── telegram_bot.py       # Alert sending + /command polling handler
├── config.py             # All tunable settings in one place
├── requirements.txt      # Python dependencies
├── .gitignore            # Excludes credentials from version control
└── README.md
```

> ⚠️ **Never commit `serviceAccountKey.json` or your Telegram token to Git.**

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- pip
- A Firebase project (free tier is fine)
- A Telegram account

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/anpr-system.git
cd anpr-system
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** EasyOCR downloads model weights (~100 MB) on first run.

### 3. Add Credentials

Place your `serviceAccountKey.json` (from Firebase console) in the project root.

### 4. Configure Settings

Edit `config.py` with your Firebase and Telegram details.

### 5. Run

```bash
python main.py
```

Press **Q** or **Ctrl+C** to stop.

---

## ⚙️ Configuration

Edit `config.py` before running:

```python
# ── Camera ──────────────────────────────────
CAMERA_SOURCE      = 0          # 0 = laptop webcam
CAMERA_ID          = "laptop_cam"

# ── Firebase ────────────────────────────────
FIREBASE_SERVICE_ACCOUNT = "serviceAccountKey.json"
FIREBASE_DATABASE_URL    = "https://your-project-id.firebaseio.com"
FIREBASE_STORAGE_BUCKET  = "your-project-id.appspot.com"

# ── Telegram ────────────────────────────────
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID   = "YOUR_CHAT_ID_HERE"

# ── Tuning ──────────────────────────────────
OCR_CONFIDENCE_THRESHOLD   = 0.70
DUPLICATE_COOLDOWN_SECONDS = 30
PROCESS_EVERY_N_FRAMES     = 5
```

---

## 🔥 Firebase Setup

1. [Firebase Console](https://console.firebase.google.com) → **Add Project**
2. Enable **Realtime Database** → Start in test mode
3. Enable **Storage** → Start in test mode
4. **Project Settings → Service Accounts → Generate new private key**
5. Save as `serviceAccountKey.json` in the project root

### Database Schema

```json
{
  "detections": {
    "-AutoKey123": {
      "plate":      "TN09AB1234",
      "confidence": 0.96,
      "timestamp":  "2025-03-14T08:22:11Z",
      "camera_id":  "laptop_cam",
      "image_url":  "https://storage.googleapis.com/...",
      "alerted":    true
    }
  },
  "watchlist": {
    "TN09AB1234": { "reason": "VIP", "priority": 1 }
  }
}
```

---

## 📬 Telegram Bot Setup

1. Message **@BotFather** → `/newbot` → copy your **Bot Token**
2. Message **@userinfobot** → copy your **Chat ID**
3. Paste both into `config.py`

---

## 🔬 How It Works

### OpenCV Pipeline

```
Frame (1280×720)
    │
    ├─ 1. cvtColor(BGR → GRAY)
    ├─ 2. bilateralFilter(d=11)        ← preserves edges, removes noise
    ├─ 3. Canny(100, 200)              ← binary edge map
    ├─ 4. findContours → approxPolyDP  ← find quadrilaterals
    ├─ 5. Filter: area 500–50000 px², aspect ratio 2.0–5.0
    ├─ 6. getPerspectiveTransform      ← 4-point warp to flat plate
    └─ 7. EasyOCR + regex ^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$
```

If no contours pass the filter, **MSER fallback** provides a second detection pass.

---

## 📊 Results

| Test Condition | Frames | Detected | Accuracy |
|---|---|---|---|
| Clear daylight, static | 120 | 113 | **94.2%** |
| Low indoor light | 80 | 66 | 82.5% |
| Plate angled ≤ 20° | 60 | 53 | 88.3% |
| Vehicle moving < 10 km/h | 50 | 39 | 78.0% |
| Night + headlights | 40 | 28 | 70.0% |

### Latency

| Stage | Average |
|---|---|
| OpenCV + OCR | ~320 ms |
| Firebase DB write | ~180 ms |
| Firebase Storage upload | ~420 ms |
| Telegram sendPhoto | ~850 ms |
| **Total detect-to-alert** | **< 2 seconds** |

---

## 🤖 Bot Commands

| Command | Action |
|---|---|
| `/start` | Show all available commands |
| `/recent` | List last 10 detections from Firebase |
| `/add_watch TN09AB1234` | Add a plate to the watchlist |
| `/del_watch TN09AB1234` | Remove a plate from the watchlist |
| `/status` | Show camera ID, cooldown, and OCR threshold |

---

## 👨‍💻 Team

| Name | Role |
|---|---|
| **Narthiban N** | Team Lead · OpenCV Pipeline & Detection |
| **Vijayan S** | Firebase Integration · Cloud Storage |
| **Thambiraj S** | Telegram Bot · System Architecture |

> Department of Computer Science & Engineering — Academic Year 2024–25

---

## 📄 License

This project is licensed under the **MIT License**.

---

## 🙏 Acknowledgements

- [EasyOCR](https://github.com/JaidedAI/EasyOCR) by JaidedAI
- [OpenCV](https://opencv.org/) — Open Source Computer Vision Library
- [Firebase](https://firebase.google.com/) by Google

---

<div align="center">
  Made with ❤️ by <b>Narthiban N · Vijayan S · Thambiraj S</b>
  <br/>Department of Computer Science & Engineering
</div>
