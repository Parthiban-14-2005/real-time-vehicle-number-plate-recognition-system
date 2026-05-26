"""
telegram_bot.py  –  Send instant Telegram alerts with plate photo + details
Also handles inbound bot commands:
  /start           → Welcome message
  /recent          → Last 10 detections from Firebase
  /add_watch <PL>  → Add plate to watchlist
  /del_watch <PL>  → Remove plate from watchlist
  /status          → System heartbeat
"""

import io
import cv2
import requests
import threading
import time
import config

# Import firebase lazily to avoid circular import
_firebase = None


def _get_firebase():
    global _firebase
    if _firebase is None:
        from firebase_client import FirebaseClient
        _firebase = FirebaseClient()
    return _firebase


class TelegramBot:
    BASE = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"

    def __init__(self):
        self.chat_id = config.TELEGRAM_CHAT_ID
        self._polling_offset = 0
        # Start background polling thread for commands
        t = threading.Thread(target=self._poll_loop, daemon=True)
        t.start()

    # ─── Send alert ───────────────────────────────────────────────────────────
    def send_alert(self, plate: str, confidence: float,
                   camera_id: str, roi, watchlist_entry: dict | None = None):
        """Send plate photo + details to the Telegram chat."""
        icon    = "⚠️" if watchlist_entry else "🚗"
        conf_pct = f"{confidence * 100:.1f}%"
        ts_str  = time.strftime("%H:%M:%S IST", time.localtime())

        caption = (
            f"{icon} *Plate detected: `{plate}`*\n"
            f"🎯 Confidence: {conf_pct}\n"
            f"📷 Camera: `{camera_id}`\n"
            f"⏱ Time: {ts_str}"
        )
        if watchlist_entry:
            reason = watchlist_entry.get("reason", "unknown")
            caption += f"\n🚨 *WATCHLIST MATCH — {reason.upper()}*"

        # Encode ROI as JPEG bytes
        _, buf  = cv2.imencode(".jpg", roi, [cv2.IMWRITE_JPEG_QUALITY, 90])
        photo   = io.BytesIO(buf.tobytes())
        photo.name = "plate.jpg"

        try:
            resp = requests.post(
                f"{self.BASE}/sendPhoto",
                data={
                    "chat_id":    self.chat_id,
                    "caption":    caption,
                    "parse_mode": "Markdown",
                },
                files={"photo": photo},
                timeout=10,
            )
            if not resp.ok:
                print(f"[Telegram] sendPhoto failed: {resp.text[:120]}")
        except Exception as e:
            print(f"[Telegram] send_alert error: {e}")

    # ─── Send plain text message ──────────────────────────────────────────────
    def send_message(self, text: str, chat_id: str | None = None):
        cid = chat_id or self.chat_id
        try:
            requests.post(
                f"{self.BASE}/sendMessage",
                json={"chat_id": cid, "text": text, "parse_mode": "Markdown"},
                timeout=8,
            )
        except Exception as e:
            print(f"[Telegram] send_message error: {e}")

    # ─── Command polling loop ─────────────────────────────────────────────────
    def _poll_loop(self):
        """Long-poll Telegram for /commands every 2 seconds."""
        while True:
            try:
                resp = requests.get(
                    f"{self.BASE}/getUpdates",
                    params={"offset": self._polling_offset, "timeout": 15},
                    timeout=20,
                )
                if resp.ok:
                    updates = resp.json().get("result", [])
                    for upd in updates:
                        self._polling_offset = upd["update_id"] + 1
                        msg = upd.get("message", {})
                        text = msg.get("text", "")
                        cid  = str(msg.get("chat", {}).get("id", ""))
                        if text:
                            self._handle_command(text.strip(), cid)
            except Exception:
                pass
            time.sleep(2)

    # ─── Command handler ──────────────────────────────────────────────────────
    def _handle_command(self, text: str, chat_id: str):
        fb = _get_firebase()
        cmd, *args = text.split()
        cmd = cmd.lower()

        if cmd == "/start":
            self.send_message(
                "👋 *ANPR Bot active*\n"
                "Commands:\n"
                "`/recent`  – last 10 detections\n"
                "`/add_watch TN09AB1234`  – add to watchlist\n"
                "`/del_watch TN09AB1234`  – remove from watchlist\n"
                "`/status`  – system status",
                chat_id,
            )

        elif cmd == "/recent":
            records = fb.get_recent(10)
            if not records:
                self.send_message("No detections yet.", chat_id)
                return
            lines = ["*Recent detections:*"]
            for r in records[:10]:
                lines.append(
                    f"• `{r.get('plate','?')}` "
                    f"{float(r.get('confidence',0))*100:.0f}%  "
                    f"{r.get('timestamp','')[:19].replace('T',' ')}"
                )
            self.send_message("\n".join(lines), chat_id)

        elif cmd == "/add_watch":
            if not args:
                self.send_message("Usage: `/add_watch TN09AB1234`", chat_id)
                return
            plate = args[0].upper()
            ok = fb.add_to_watchlist(plate)
            msg = f"✅ `{plate}` added to watchlist." if ok else f"❌ Failed to add `{plate}`."
            self.send_message(msg, chat_id)

        elif cmd == "/del_watch":
            if not args:
                self.send_message("Usage: `/del_watch TN09AB1234`", chat_id)
                return
            plate = args[0].upper()
            try:
                fb.watchlist_ref.child(plate).delete()
                self.send_message(f"✅ `{plate}` removed from watchlist.", chat_id)
            except Exception:
                self.send_message(f"❌ Could not remove `{plate}`.", chat_id)

        elif cmd == "/status":
            self.send_message(
                "🟢 *ANPR system is running*\n"
                f"Camera: `{config.CAMERA_ID}`\n"
                f"Cooldown: {config.DUPLICATE_COOLDOWN_SECONDS}s\n"
                f"OCR threshold: {config.OCR_CONFIDENCE_THRESHOLD*100:.0f}%",
                chat_id,
            )
