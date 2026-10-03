"""OpenCV USB webcam adapter."""
import asyncio
import logging
import cv2

logger = logging.getLogger("ultron.adapters.laptop.camera")

class OpenCVCamera:
    def __init__(self, config: dict):
        idx = config.get("camera",{}).get("device_index", 0)
        self._cap = cv2.VideoCapture(idx)
        if not self._cap.isOpened():
            logger.warning(f"Camera {idx} not available.")

    async def capture_frame(self):
        return await asyncio.to_thread(self._read)

    def _read(self):
        ret, frame = self._cap.read()
        return frame if ret else None

    async def release(self):
        self._cap.release()

def create(config: dict) -> OpenCVCamera:
    return OpenCVCamera(config)
