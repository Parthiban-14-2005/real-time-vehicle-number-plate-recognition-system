"""
firebase_client.py  –  Firebase Realtime DB + Cloud Storage integration
Handles:
  • Saving detection events
  • Uploading plate crop images
  • Watchlist lookups
  • In-memory duplicate suppression (30-second cooldown)
"""

import io
import cv2
import firebase_admin
from firebase_admin import credentials, db, storage
from datetime import datetime, timedelta
import config


class FirebaseClient:
    def __init__(self):
        try:
            cred = credentials.Certificate(config.FIREBASE_SERVICE_ACCOUNT)
            firebase_admin.initialize_app(cred, {
                "databaseURL":   config.FIREBASE_DATABASE_URL,
                "storageBucket": config.FIREBASE_STORAGE_BUCKET,
            })
            self.detections_ref = db.reference("detections")
            self.watchlist_ref  = db.reference("watchlist")
            self._seen: dict[str, datetime] = {}   # { plate: last_seen_utc }
            print("[Firebase] Connected successfully.")
        except Exception as e:
            print(f"[Firebase] Init failed: {e}")
            print("[Firebase] Running in OFFLINE mode (detections not saved).")
            self.detections_ref = None
            self.watchlist_ref  = None
            self._seen = {}

    # ─── Duplicate guard ──────────────────────────────────────────────────────
    def is_duplicate(self, plate: str) -> bool:
        """Return True if this plate was already processed within the cooldown window."""
        now  = datetime.utcnow()
        last = self._seen.get(plate)
        if last and (now - last).seconds < config.DUPLICATE_COOLDOWN_SECONDS:
            return True
        self._seen[plate] = now
        return False

    # ─── Save detection ───────────────────────────────────────────────────────
    def save_detection(self, plate: str, confidence: float,
                       camera_id: str, roi) -> str | None:
        """
        Push detection record to Firebase Realtime DB.
        Uploads cropped plate image to Cloud Storage.
        Returns the Firebase push key or None on failure.
        """
        if self.detections_ref is None:
            return None

        try:
            image_url = self._upload_plate_image(plate, roi)
            record = {
                "plate":      plate,
                "confidence": round(float(confidence), 4),
                "timestamp":  datetime.utcnow().isoformat() + "Z",
                "camera_id":  camera_id,
                "image_url":  image_url or "",
                "alerted":    True,
            }
            ref = self.detections_ref.push(record)
            print(f"[Firebase] Saved  {plate}  key={ref.key}")
            return ref.key
        except Exception as e:
            print(f"[Firebase] save_detection error: {e}")
            return None

    # ─── Watchlist lookup ─────────────────────────────────────────────────────
    def check_watchlist(self, plate: str) -> dict | None:
        """
        Return watchlist entry dict  {reason, priority, ...}  or None.
        Example Firebase node:
          watchlist/TN09AB1234 → { "reason": "VIP", "priority": 1 }
        """
        if self.watchlist_ref is None:
            return None
        try:
            return self.watchlist_ref.child(plate).get()
        except Exception:
            return None

    def add_to_watchlist(self, plate: str, reason: str = "manual",
                         priority: int = 1) -> bool:
        if self.watchlist_ref is None:
            return False
        try:
            self.watchlist_ref.child(plate).set({
                "reason":    reason,
                "priority":  priority,
                "added_at":  datetime.utcnow().isoformat() + "Z",
            })
            return True
        except Exception:
            return False

    # ─── Fetch recent detections ──────────────────────────────────────────────
    def get_recent(self, limit: int = 20) -> list[dict]:
        """Return last `limit` detection records (newest first)."""
        if self.detections_ref is None:
            return []
        try:
            snapshot = (self.detections_ref
                        .order_by_child("timestamp")
                        .limit_to_last(limit)
                        .get())
            if not snapshot:
                return []
            records = list(snapshot.values())
            return sorted(records, key=lambda r: r.get("timestamp", ""), reverse=True)
        except Exception as e:
            print(f"[Firebase] get_recent error: {e}")
            return []

    # ─── Private: upload image ────────────────────────────────────────────────
    def _upload_plate_image(self, plate: str, roi) -> str | None:
        """Upload cropped plate JPG to Firebase Cloud Storage; return public URL."""
        try:
            bucket = storage.bucket()
            ts     = int(datetime.utcnow().timestamp())
            path   = f"plates/{plate}_{ts}.jpg"
            blob   = bucket.blob(path)

            _, buf  = cv2.imencode(".jpg", roi, [cv2.IMWRITE_JPEG_QUALITY, 92])
            blob.upload_from_string(buf.tobytes(), content_type="image/jpeg")
            blob.make_public()
            return blob.public_url
        except Exception as e:
            print(f"[Firebase] image upload error: {e}")
            return None
