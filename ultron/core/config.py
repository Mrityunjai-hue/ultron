"""
ULTRON — Core Configuration
─────────────────────────────────────────────────────────────────────────────
Handles environment loading, credential resolution, audio parameters,
and model settings with clean production filesystem separation.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field

from ultron.core.paths import get_user_data_dir, get_app_install_dir
from ultron.core.credentials import get_credential_manager
from ultron.core.user_config import UserConfig, load_user_config


def load_dotenv_fallback():
    """Loads .env file only when running in non-frozen development mode."""
    if getattr(sys, "frozen", False):
        return
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

load_dotenv_fallback()


def _get_env_float(name: str, default: float) -> float:
    try:
        val = os.getenv(name)
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default

def _get_env_int(name: str, default: int) -> int:
    try:
        val = os.getenv(name)
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default

def _get_env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "on")

@dataclass
class AudioConfig:
    input_sample_rate: int = 16000        # 16 kHz PCM16 for Gemini Live input
    output_sample_rate: int = 24000       # 24 kHz PCM16 for Gemini Live output
    channels: int = 1
    chunk_size: int = 512                 # 32ms frames @ 16kHz
    speech_onset_rms_threshold: float = field(
        default_factory=lambda: _get_env_float("ULTRON_SPEECH_ONSET_RMS", 0.025)
    ) # Calibrated human voice onset threshold for instant visual/audio feedback
    barge_in_rms_threshold: float = field(
        default_factory=lambda: _get_env_float("ULTRON_BARGE_IN_RMS", _get_env_float("BARGE_IN_RMS_THRESHOLD", 0.15))
    ) # Calibrated vocal energy during speaker playback
    barge_in_consecutive_frames: int = field(
        default_factory=lambda: _get_env_int("ULTRON_BARGE_IN_FRAMES", _get_env_int("BARGE_IN_CONSECUTIVE_FRAMES", 3))
    ) # 96ms debounce to reject clicks/room noise/speaker bleed
    enable_local_barge_in: bool = field(
        default_factory=lambda: _get_env_bool("ULTRON_ENABLE_LOCAL_BARGE_IN", True)
    ) # Toggle local energy-based playback cancellation


@dataclass
class ModelConfig:
    model: str = field(
        default_factory=lambda: os.getenv("ULTRON_MODEL", "gemini-2.5-flash-native-audio-latest")
    )  # Primary Gemini Live bidiGenerateContent model (e.g. gemini-2.5-flash-native-audio-latest or gemini-2.0-flash-exp)
    voice_name: str = "Puck"                             # Options: Aoede, Charon, Fenrir, Kore, Puck
    system_instruction: str = (
        "You are ULTRON, a sovereign, concise, calculating AI entity. "
        "Speak naturally in short, authoritative sentences. "
        "Never use markdown, lists, or conversational filler. "
        "Use provided tools whenever system status, time, files, or applications are requested."
    )


from ultron.core.identity import build_system_instruction


@dataclass
class UltronConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    gemini_api_key: str = ""
    workspace_root: Path = field(default_factory=get_user_data_dir)
    install_root: Path = field(default_factory=get_app_install_dir)
    user: Optional[UserConfig] = None

    def __post_init__(self):
        if not self.gemini_api_key:
            cred_mgr = get_credential_manager()
            self.gemini_api_key = cred_mgr.get_api_key("GEMINI_API_KEY") or ""

        if self.user is None:
            self.user = load_user_config()

        assistant_name = self.user.assistant_name if (self.user and self.user.assistant_name) else "ULTRON"
        owner_name = self.user.owner_name if (self.user and self.user.owner_name) else None
        addressing = self.user.addressing_name if (self.user and self.user.addressing_name) else owner_name

        if self.user and self.user.first_run_completed and self.user.voice_preference:
            self.model.voice_name = self.user.voice_preference

        self.model.system_instruction = build_system_instruction(
            assistant_name=assistant_name,
            owner_name=owner_name,
            addressing_name=addressing,
        )


def get_config() -> UltronConfig:
    """Returns singleton-like active configuration instance."""
    return UltronConfig()

