"""
Real-Time Vehicle Number Plate Recognition System
Uses laptop webcam (cv2.VideoCapture(0))
Stack: OpenCV · EasyOCR · Firebase Realtime DB · Telegram Bot
"""

import cv2
import threading
import time
import signal
import sys
from detector import PlateDetector
from firebase_client import FirebaseClient
from telegram_bot import TelegramBot
import config

# ─── Graceful shutdown ────────────────────────────────────────────────────────
_running = True

def _signal_handler(sig, frame):
    global _running
    print("\n[INFO] Shutting down …")
    _running = False

signal.signal(signal.SIGINT, _signal_handler)


# ─── Main capture loop ────────────────────────────────────────────────────────
def run():
    print("[INFO] Initialising ANPR system …")

    firebase = FirebaseClient()
    bot      = TelegramBot()
    detector = PlateDetector()

    # Open laptop webcam (index 0). Change to RTSP URL string for IP cam.
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Cannot open webcam. Check device index in config.py")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          config.CAPTURE_FPS)

    print(f"[INFO] Webcam opened  ({config.FRAME_WIDTH}x{config.FRAME_HEIGHT})")
    print(f"[INFO] Press  Q  or Ctrl+C to quit\n")

    frame_count  = 0
    process_every = config.PROCESS_EVERY_N_FRAMES   # skip frames for speed

    while _running:
        ret, frame = cap.read()
        if not ret:
            print("[WARN] Frame grab failed – retrying …")
            time.sleep(0.05)
            continue

        frame_count += 1

        # ── Draw live preview overlay ─────────────────────────────────────
        cv2.putText(frame, "ANPR LIVE", (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 80), 2)
        cv2.putText(frame, f"Frame #{frame_count}", (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # ── Run detection on every Nth frame ─────────────────────────────
        if frame_count % process_every == 0:
            results = detector.detect(frame.copy(), camera_id=config.CAMERA_ID)

            for plate_text, confidence, roi, bbox in results:
                x, y, w, h = bbox
                # Green bounding box around detected plate
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 230, 80), 2)
                cv2.putText(frame, f"{plate_text}  {confidence*100:.0f}%",
                            (x, y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 230, 80), 2)

                if not firebase.is_duplicate(plate_text):
                    # Save to Firebase (non-blocking thread)
                    threading.Thread(
                        target=firebase.save_detection,
                        args=(plate_text, confidence, config.CAMERA_ID, roi),
                        daemon=True
                    ).start()

                    # Send Telegram alert (non-blocking thread)
                    threading.Thread(
                        target=bot.send_alert,
                        args=(plate_text, confidence, config.CAMERA_ID, roi,
                              firebase.check_watchlist(plate_text)),
                        daemon=True
                    ).start()

                    print(f"[DETECTED] {plate_text}  conf={confidence*100:.1f}%  cam={config.CAMERA_ID}")

        # ── Show live window ──────────────────────────────────────────────
        cv2.imshow("ANPR – Press Q to quit", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] ANPR system stopped.")


if __name__ == "__main__":
    run()
