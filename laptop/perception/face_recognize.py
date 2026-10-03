"""
ULTRON Perception — Face Recognition & Real-Time Gaze Tracking v2.0
─────────────────────────────────────────────────────────────────────────────
Features:
- Real-time OpenCV Haar Cascade face tracking (60fps on CPU)
- Gaze vector computation steering character eyes (-14 to +14px horizontal, -10 to +10px vertical)
- Dual-engine biometric identification:
    1. dlib / face_recognition 128-d embeddings (if available)
    2. Zero-dependency OpenCV normalized 64x64 histogram-equalized template vector matching
- Dynamic integration with SQLite MemoryDB
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import asyncio
import logging
import os
import cv2
import json
import sqlite3
import numpy as np
from typing import Optional, Dict, Tuple

logger = logging.getLogger("ultron.perception.face_recognize")

class FaceRecognizer:
    def __init__(self, config: dict):
        self.config = config
        self.threshold = config.get("perception", {}).get("face_threshold", 0.76)
        self.db_path = config.get("memory", {}).get("db_path", "data/memory.db")
        if not os.path.isabs(self.db_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(base_dir, self.db_path)

        self._known_dlib = {}
        self._known_templates = {}
        self._cascade = None
        self._fr = None
        self._initialized = False

    async def _ensure_init(self):
        if self._initialized:
            return

        # 1. OpenCV Haar Cascade (Fast face detection & gaze centering)
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._cascade = cv2.CascadeClassifier(cascade_path)
            logger.info("OpenCV Haar Cascade initialized for face tracking.")
        except Exception as e:
            logger.warning(f"Could not load OpenCV cascade: {e}")

        # 2. Check face_recognition library (dlib)
        try:
            import face_recognition as fr
            self._fr = fr
            logger.info("face_recognition (dlib) engine active.")
        except ImportError:
            self._fr = None
            logger.info("Using OpenCV biometric template engine (dlib not present).")

        # 3. Load all templates from SQLite
        await self._load_embeddings()
        self._initialized = True

    async def _load_embeddings(self):
        if not os.path.exists(self.db_path):
            return
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT name, face_embedding, face_metadata FROM users WHERE face_embedding IS NOT NULL")
            for name, blob, meta_raw in cur.fetchall():
                if not blob:
                    continue
                meta = json.loads(meta_raw) if meta_raw else {}
                mtype = meta.get("type", "")

                if mtype == "dlib_128" or len(blob) == 128 * 8:
                    emb = np.frombuffer(blob, dtype=np.float64)
                    self._known_dlib[name] = emb
                else:
                    # OpenCV 64x64 template (4096 float32)
                    vec = np.frombuffer(blob, dtype=np.float32)
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec = vec / norm
                    self._known_templates[name] = vec

            conn.close()
            total = len(self._known_dlib) + len(self._known_templates)
            logger.info(f"Loaded {total} enrolled face biometric template(s) from SQLite.")
        except Exception as e:
            logger.debug(f"Memory DB load note: {e}")

    async def reload_faces(self):
        """Refreshes known faces after new enrollment."""
        self._known_dlib.clear()
        self._known_templates.clear()
        await self._load_embeddings()

    async def recognize(self, frame) -> Optional[dict]:
        await self._ensure_init()
        if frame is None:
            return None
        return await asyncio.to_thread(self._sync_recognize, frame)

    def _sync_recognize(self, frame) -> Optional[dict]:
        if frame is None or self._cascade is None:
            return None
        h, w = frame.shape[:2]

        # 1. Detect Face Coordinates via OpenCV
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=4, minSize=(60, 60))

        if len(faces) == 0:
            return None

        # Pick largest face (closest to camera)
        fx, fy, fw, fh = max(faces, key=lambda b: b[2] * b[3])
        face_cx = fx + fw / 2.0
        face_cy = fy + fh / 2.0

        # Normalized coordinates relative to frame center (-1.0 to +1.0)
        norm_x = (face_cx - w / 2.0) / (w / 2.0)
        norm_y = (face_cy - h / 2.0) / (h / 2.0)

        # Gaze coordinates for UI character (-14 to +14 px horizontal, -10 to +10 px vertical)
        # Note: Inverted X so if user moves right in webcam, ULTRON looks towards them
        gaze_x = -norm_x * 14.0
        gaze_y = norm_y * 10.0

        result = {
            "name": "UNKNOWN",
            "confidence": 0.5,
            "gaze_x": gaze_x,
            "gaze_y": gaze_y,
            "bbox": (int(fx), int(fy), int(fw), int(fh))
        }

        # 2. Biometric Recognition — OpenCV Template Matching Engine
        if self._known_templates:
            try:
                face_roi = gray[fy:fy+fh, fx:fx+fw]
                resized = cv2.resize(face_roi, (64, 64))
                equalized = cv2.equalizeHist(resized)
                curr_vec = equalized.astype(np.float32).flatten()
                norm = np.linalg.norm(curr_vec)
                if norm > 0:
                    curr_vec = curr_vec / norm

                best_sim = -1.0
                best_name = None
                for name, known_vec in self._known_templates.items():
                    sim = float(np.dot(curr_vec, known_vec))
                    if sim > best_sim:
                        best_sim = sim
                        best_name = name

                if best_name and best_sim >= self.threshold:
                    result["name"] = best_name
                    result["confidence"] = round(best_sim, 2)
            except Exception as e:
                logger.debug(f"Template match note: {e}")

        # 3. Biometric Recognition — dlib fallback if available
        if result["name"] == "UNKNOWN" and self._fr and self._known_dlib:
            try:
                rgb = frame[:, :, ::-1]
                encs = self._fr.face_encodings(rgb, [(fy, fx + fw, fy + fh, fx)])
                if encs:
                    enc = encs[0]
                    known_names = list(self._known_dlib.keys())
                    known_vecs = list(self._known_dlib.values())
                    dists = self._fr.face_distance(known_vecs, enc)
                    best_idx = int(np.argmin(dists))
                    dist = float(dists[best_idx])
                    conf = max(0.0, 1.0 - dist)
                    if dist <= 0.45:
                        result["name"] = known_names[best_idx]
                        result["confidence"] = round(conf, 2)
            except Exception as e:
                logger.debug(f"dlib match note: {e}")

        return result
