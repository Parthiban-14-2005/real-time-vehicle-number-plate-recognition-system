"""
detector.py  –  OpenCV image processing + EasyOCR pipeline
Returns a list of (plate_text, confidence, roi_image, bbox) tuples.
"""

import cv2
import re
import numpy as np
import easyocr
import config


class PlateDetector:
    """
    Full pipeline:
      frame → preprocess → find plate candidates (contours) →
      perspective warp → EasyOCR → regex filter → results
    """

    def __init__(self):
        print("[INFO] Loading EasyOCR model (first run downloads ~100 MB) …")
        self.reader  = easyocr.Reader(config.OCR_LANGUAGES, gpu=config.USE_GPU)
        self.plate_re = re.compile(config.PLATE_REGEX)
        print("[INFO] EasyOCR ready.")

    # ─── Public API ───────────────────────────────────────────────────────────
    def detect(self, frame, camera_id="cam"):
        """
        Args:
            frame     : BGR numpy array from cv2.VideoCapture
            camera_id : string label (stored to Firebase)
        Returns:
            list of (plate_text, confidence, roi_bgr, bbox)
            bbox = (x, y, w, h) in original frame coords
        """
        edges = self._preprocess(frame)
        candidates = self._find_plate_candidates(frame, edges)
        results = []

        for roi, bbox in candidates:
            plate, conf = self._run_ocr(roi)
            if plate and conf >= config.OCR_CONFIDENCE_THRESHOLD:
                results.append((plate, conf, roi, bbox))

        return results

    # ─── Step 1 : Preprocessing ───────────────────────────────────────────────
    def _preprocess(self, frame):
        # Resize to standard size for consistent processing
        resized = cv2.resize(frame, (1280, 720))

        # Convert to grayscale
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        # Bilateral filter – smooths noise while keeping edges sharp
        bilateral = cv2.bilateralFilter(gray, 11, 17, 17)

        # Canny edge detection
        edges = cv2.Canny(bilateral,
                          config.CANNY_THRESHOLD1,
                          config.CANNY_THRESHOLD2)
        return edges

    # ─── Step 2 : Find plate region candidates ───────────────────────────────
    def _find_plate_candidates(self, frame, edges):
        """
        Returns list of (roi, bbox) where roi is cropped + warped plate image.
        """
        contours, _ = cv2.findContours(
            edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Sort by area (largest first) and check top N
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:15]

        candidates = []
        for c in contours:
            peri   = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.018 * peri, True)

            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                area   = w * h
                aspect = w / float(h) if h > 0 else 0

                if (config.MIN_PLATE_AREA < area < config.MAX_PLATE_AREA and
                        config.MIN_ASPECT_RATIO < aspect < config.MAX_ASPECT_RATIO):

                    roi = self._warp_plate(frame, approx, w, h)
                    candidates.append((roi, (x, y, w, h)))

        # Fallback: sliding window if contours miss the plate
        if not candidates:
            candidates = self._sliding_window_fallback(frame)

        return candidates

    # ─── Step 3 : Perspective warp ────────────────────────────────────────────
    def _warp_plate(self, frame, approx, w, h):
        """
        Four-point perspective transform to get a bird's-eye view of the plate.
        """
        pts = approx.reshape(4, 2).astype(np.float32)

        # Order: top-left, top-right, bottom-right, bottom-left
        rect = self._order_points(pts)
        dst  = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
        M    = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(frame, M, (w, h))
        return warped

    @staticmethod
    def _order_points(pts):
        rect = np.zeros((4, 2), dtype=np.float32)
        s    = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]   # top-left
        rect[2] = pts[np.argmax(s)]   # bottom-right
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # top-right
        rect[3] = pts[np.argmax(diff)]  # bottom-left
        return rect

    # ─── Step 4 : OCR ─────────────────────────────────────────────────────────
    def _run_ocr(self, roi):
        """
        Runs EasyOCR on the warped ROI.
        Returns (cleaned_plate_string, confidence) or (None, 0).
        """
        # Upscale small ROIs – OCR accuracy drops on tiny images
        h, w = roi.shape[:2]
        if w < 200:
            roi = cv2.resize(roi, (200, int(200 * h / w)))

        # Sharpen with unsharp mask
        blur     = cv2.GaussianBlur(roi, config.GAUSSIAN_KERNEL, 0)
        sharpened = cv2.addWeighted(roi, 1.5, blur, -0.5, 0)

        results = self.reader.readtext(sharpened, detail=1,
                                       allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

        best_text, best_conf = None, 0.0
        for (_, text, conf) in results:
            cleaned = text.upper().replace(" ", "").replace("-", "")
            if self.plate_re.match(cleaned) and conf > best_conf:
                best_text = cleaned
                best_conf = conf

        return best_text, best_conf

    # ─── Fallback: sliding window ─────────────────────────────────────────────
    def _sliding_window_fallback(self, frame):
        """
        When contour detection misses, try a denser search via MSER regions.
        """
        candidates = []
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mser  = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)

        for region in regions:
            x, y, w, h = cv2.boundingRect(region.reshape(-1, 1, 2))
            area   = w * h
            aspect = w / float(h) if h > 0 else 0
            if (config.MIN_PLATE_AREA < area < config.MAX_PLATE_AREA and
                    config.MIN_ASPECT_RATIO < aspect < config.MAX_ASPECT_RATIO):
                roi = frame[y:y+h, x:x+w]
                candidates.append((roi, (x, y, w, h)))

        return candidates[:5]   # cap at 5 fallback candidates
