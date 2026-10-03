"""
ULTRON Arduino UNO R4 WiFi Companion Hardware Bridge
─────────────────────────────────────────────────────────────────────────────
Features:
- Auto-detects Arduino UNO R4 WiFi on USB Serial (115200 baud) or uses configured port
- Mirrors ULTRON FSM states to the onboard 8x12 LED matrix (IDLE, LISTEN, THINK, SPEAK, SLEEP, ALERT)
- Bi-directional serial protocol with JSON command frames
- Receives wake triggers and physical button events from the companion hardware
- Non-blocking asynchronous design with automatic graceful fallback to virtual mode
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import asyncio
import json
import logging
import time
from typing import Optional, Callable

logger = logging.getLogger("ultron.adapters.arduino")

class ArduinoBridge:
    def __init__(self, config: dict):
        self.config = config
        self.port_name = config.get("arduino", {}).get("port", "auto")
        self.baud = config.get("arduino", {}).get("baud", 115200)
        self.enabled = config.get("arduino", {}).get("enabled", True)
        self._serial = None
        self._running = False
        self._on_wake_callback: Optional[Callable[[], None]] = None

    def set_wake_callback(self, callback: Callable[[], None]):
        self._on_wake_callback = callback

    async def start(self):
        """Attempts connection and starts background read loop."""
        if not self.enabled:
            logger.info("Arduino UNO R4 bridge disabled in config.")
            return

        self._running = True
        await asyncio.to_thread(self._connect_sync)
        if self._serial and self._serial.is_open:
            asyncio.create_task(self._read_loop())

    def _connect_sync(self):
        try:
            import serial
            import serial.tools.list_ports
        except ImportError:
            logger.info("pyserial not available. Arduino bridge running in virtual mode.")
            return

        target_port = None
        if self.port_name and self.port_name.lower() != "auto":
            target_port = self.port_name
        else:
            # Auto-detect Arduino or USB Serial device
            ports = list(serial.tools.list_ports.comports())
            for p in ports:
                desc = (p.description or "").lower()
                hwid = (p.hwid or "").lower()
                if "arduino" in desc or "uno" in desc or "ch340" in desc or "usb serial" in desc:
                    target_port = p.device
                    break
            if not target_port and ports:
                target_port = ports[0].device

        if not target_port:
            logger.info("Arduino UNO R4 WiFi not detected on serial ports. Running in virtual mode.")
            return

        try:
            self._serial = serial.Serial(target_port, self.baud, timeout=1.0)
            time.sleep(1.8) # Allow Arduino bootloader reset
            logger.info(f"Connected to Arduino UNO R4 WiFi on {target_port} at {self.baud} baud.")
            # Send initial sync
            self._serial.write(b'{"type":"setState","state":"idle"}\n')
        except Exception as e:
            logger.info(f"Could not open Arduino serial port ({target_port}): {e}. Running in virtual mode.")
            self._serial = None

    async def send_state(self, state: str):
        """Sends state transition to Arduino to update 8x12 LED matrix."""
        if not self._serial or not self._serial.is_open:
            return
        cmd = json.dumps({"type": "setState", "state": state.lower()}) + "\n"
        await asyncio.to_thread(self._write_sync, cmd.encode("utf-8"))

    def _write_sync(self, data: bytes):
        try:
            if self._serial and self._serial.is_open:
                self._serial.write(data)
                self._serial.flush()
        except Exception as e:
            logger.debug(f"Serial write note: {e}")

    async def _read_loop(self):
        """Background loop reading events from Arduino."""
        while self._running and self._serial and self._serial.is_open:
            try:
                line = await asyncio.to_thread(self._serial.readline)
                if line:
                    line_str = line.decode("utf-8", errors="ignore").strip()
                    if line_str.startswith("{"):
                        try:
                            msg = json.loads(line_str)
                            msg_type = msg.get("type", "")
                            if msg_type == "event":
                                evt = msg.get("event", "")
                                if evt == "wakeword_detected" and self._on_wake_callback:
                                    logger.info("Hardware wake trigger received from Arduino UNO R4!")
                                    self._on_wake_callback()
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"Serial read loop note: {e}")
                await asyncio.sleep(2.0)
            await asyncio.sleep(0.05)

    async def close(self):
        self._running = False
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None

def create(config: dict) -> ArduinoBridge:
    return ArduinoBridge(config)
