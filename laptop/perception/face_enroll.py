"""
ULTRON Perception — Face Enrollment v2.0
Registers a user in persistent SQLite memory using OpenCV normalized face templates
with automatic biometric fallback.
"""
from __future__ import annotations
import asyncio
import logging
import os
import cv2
import numpy as np
from typing import Optional

logger = logging.getLogger("ultron.perception.face_enroll")

class FaceEnroller:
    def __init__(self, config: dict):
        self.config = config
        self._cascade = None
        self._init_cascade()

    def _init_cascade(self):
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._cascade = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            logger.warning(f"Error loading cascade: {e}")

    async def enroll(self, frame, name: str) -> bool:
        return await asyncio.to_thread(self._sync_enroll, frame, name)

    def _sync_enroll(self, frame, name: str) -> bool:
        if frame is None:
            logger.warning("Enrollment failed: empty video frame.")
            return False

        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=4, minSize=(60, 60))

        if len(faces) == 0:
            logger.warning("No face detected in frame during enrollment attempt.")
            return False

        # Pick largest face
        fx, fy, fw, fh = max(faces, key=lambda b: b[2] * b[3])

        # 1. Try face_recognition (dlib) if installed
        try:
            import face_recognition as fr
            rgb = frame[:, :, ::-1]
            encs = fr.face_encodings(rgb, [(fy, fx + fw, fy + fh, fx)])
            if encs:
                blob = encs[0].astype(np.float64).tobytes()
                self._persist(name, blob, {"type": "dlib_128", "bbox": [int(fx), int(fy), int(fw), int(fh)]})
                logger.info(f"Biometric enrollment (dlib) successful for: {name}")
                return True
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"dlib enrollment note: {e}")

        # 2. OpenCV Normalized Face ROI Template (Zero-Dependency Engine)
        face_roi = gray[fy:fy+fh, fx:fx+fw]
        resized = cv2.resize(face_roi, (64, 64))
        equalized = cv2.equalizeHist(resized)
        vec = equalized.astype(np.float32).flatten()
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        blob = vec.tobytes()
        self._persist(name, blob, {"type": "opencv_template_64", "bbox": [int(fx), int(fy), int(fw), int(fh)]})
        logger.info(f"OpenCV template enrollment successful for: {name}")
        return True

    def _persist(self, name: str, blob: bytes, metadata: dict):
        from memory.db import MemoryDB
        db = MemoryDB(self.config)
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cur = conn.cursor()
        import json
        cur.execute("""
            INSERT INTO users (name, face_embedding, face_metadata, last_seen, recognition_count)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, 1)
            ON CONFLICT(name) DO UPDATE SET
                face_embedding = excluded.face_embedding,
                face_metadata  = excluded.face_metadata,
                last_seen      = CURRENT_TIMESTAMP
        """, (name, blob, json.dumps(metadata)))
        conn.commit()
        conn.close()
