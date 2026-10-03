"""
ULTRON — Secure Windows Credential Storage Interface
─────────────────────────────────────────────────────────────────────────────
Provides hardware/user-backed Windows DPAPI (Data Protection API) encryption
for storing sensitive API keys locally without plaintext persistence.
Provides secure fallback to environment variables for CI/CD and automated testing.

CRITICAL SECURITY REQUIREMENT:
- Decrypted credential values are never logged, printed, or exposed outside the
  immediate client initialization call.
- Safe inquiry methods (has_credential, get_status) return boolean/status only.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import os
import sys
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any

from ultron.core.paths import get_config_dir

logger = logging.getLogger("ultron.core.credentials")

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    def _dpapi_encrypt(data: bytes, description: str = "ULTRON Protected Credential") -> bytes:
        blob_in = DATA_BLOB(
            len(data),
            ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_byte)),
        )
        blob_out = DATA_BLOB()
        if not ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(blob_in),
            description,
            None,
            None,
            None,
            0,
            ctypes.byref(blob_out),
        ):
            raise ctypes.WinError()
        res = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return res

    def _dpapi_decrypt(cipher: bytes) -> bytes:
        blob_in = DATA_BLOB(
            len(cipher),
            ctypes.cast(ctypes.create_string_buffer(cipher), ctypes.POINTER(ctypes.c_byte)),
        )
        blob_out = DATA_BLOB()
        if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(blob_out),
        ):
            raise ctypes.WinError()
        res = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return res
else:
    def _dpapi_encrypt(data: bytes, description: str = "") -> bytes:
        raise NotImplementedError("DPAPI is only available on Windows.")

    def _dpapi_decrypt(cipher: bytes) -> bytes:
        raise NotImplementedError("DPAPI is only available on Windows.")


class BaseCredentialStore(ABC):
    """Abstract interface for secure credential acquisition and persistence."""

    @abstractmethod
    def get_api_key(self, key_name: str = "GEMINI_API_KEY") -> Optional[str]:
        """Retrieves decrypted API key for client initialization. Never log the returned value."""
        pass

    @abstractmethod
    def set_api_key(self, key_name: str, key_value: str) -> bool:
        """Stores API key encrypted in secure store."""
        pass

    @abstractmethod
    def delete_api_key(self, key_name: str) -> bool:
        """Removes API key from secure store."""
        pass

    @abstractmethod
    def has_api_key(self, key_name: str = "GEMINI_API_KEY") -> bool:
        """Safe non-revealing existence check."""
        pass


class WindowsDPAPICredentialStore(BaseCredentialStore):
    """Stores credentials encrypted on disk using user-bound Windows DPAPI."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or get_config_dir()
        self.cred_file = self.config_dir / "credentials.dpapi"

    def _load_raw(self) -> Dict[str, bytes]:
        if not self.cred_file.exists():
            return {}
        try:
            with open(self.cred_file, "rb") as f:
                cipher_data = f.read()
            if not cipher_data:
                return {}
            plain_data = _dpapi_decrypt(cipher_data)
            import json
            parsed = json.loads(plain_data.decode("utf-8"))
            return parsed if isinstance(parsed, dict) else {}
        except Exception as e:
            logger.debug(f"[Credential Store] Unable to decrypt DPAPI store: {e}")
            return {}

    def _save_raw(self, data: Dict[str, str]) -> bool:
        try:
            import json
            plain_bytes = json.dumps(data).encode("utf-8")
            cipher_bytes = _dpapi_encrypt(plain_bytes)
            self.cred_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cred_file, "wb") as f:
                f.write(cipher_bytes)
            return True
        except Exception as e:
            logger.error(f"[Credential Store] Failed encrypting DPAPI store: {e}")
            return False

    def get_api_key(self, key_name: str = "GEMINI_API_KEY") -> Optional[str]:
        if sys.platform != "win32":
            return None
        data = self._load_raw()
        val = data.get(key_name)
        return str(val) if val else None

    def set_api_key(self, key_name: str, key_value: str) -> bool:
        if sys.platform != "win32":
            return False
        data = self._load_raw()
        data[key_name] = key_value.strip()
        return self._save_raw(data)

    def delete_api_key(self, key_name: str) -> bool:
        if sys.platform != "win32":
            return False
        data = self._load_raw()
        if key_name in data:
            del data[key_name]
            return self._save_raw(data)
        return True

    def has_api_key(self, key_name: str = "GEMINI_API_KEY") -> bool:
        if sys.platform != "win32":
            return False
        data = self._load_raw()
        return bool(data.get(key_name))


class EnvironmentCredentialStore(BaseCredentialStore):
    """Retrieves credentials from environment variables for developer and CI/CD use."""

    def get_api_key(self, key_name: str = "GEMINI_API_KEY") -> Optional[str]:
        val = os.environ.get(key_name, "").strip()
        if not val and key_name == "GEMINI_API_KEY":
            val = os.environ.get("GOOGLE_API_KEY", "").strip()
        return val if val else None

    def set_api_key(self, key_name: str, key_value: str) -> bool:
        os.environ[key_name] = key_value.strip()
        return True

    def delete_api_key(self, key_name: str) -> bool:
        if key_name in os.environ:
            del os.environ[key_name]
        return True

    def has_api_key(self, key_name: str = "GEMINI_API_KEY") -> bool:
        return bool(self.get_api_key(key_name))


class SecureCredentialManager(BaseCredentialStore):
    """
    Authoritative composite credential manager.
    Queries Windows DPAPI store first, falling back to process environment.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        self.dpapi_store = WindowsDPAPICredentialStore(config_dir)
        self.env_store = EnvironmentCredentialStore()

    def get_api_key(self, key_name: str = "GEMINI_API_KEY") -> Optional[str]:
        # 1. DPAPI secure local store
        val = self.dpapi_store.get_api_key(key_name)
        if val:
            return val
        # 2. Process environment
        return self.env_store.get_api_key(key_name)

    def set_api_key(self, key_name: str, key_value: str) -> bool:
        if sys.platform == "win32":
            return self.dpapi_store.set_api_key(key_name, key_value)
        return self.env_store.set_api_key(key_name, key_value)

    def delete_api_key(self, key_name: str) -> bool:
        dpapi_res = self.dpapi_store.delete_api_key(key_name)
        env_res = self.env_store.delete_api_key(key_name)
        return dpapi_res or env_res

    def has_api_key(self, key_name: str = "GEMINI_API_KEY") -> bool:
        return self.dpapi_store.has_api_key(key_name) or self.env_store.has_api_key(key_name)

    def get_storage_type(self, key_name: str = "GEMINI_API_KEY") -> str:
        """Returns non-sensitive descriptor of where the key is stored (DPAPI, ENV, or NONE)."""
        if self.dpapi_store.has_api_key(key_name):
            return "WINDOWS_DPAPI"
        if self.env_store.has_api_key(key_name):
            return "ENVIRONMENT_VARIABLE"
        return "NOT_CONFIGURED"


_CREDENTIAL_MANAGER_INSTANCE: Optional[SecureCredentialManager] = None

def get_credential_manager() -> SecureCredentialManager:
    """Singleton getter for the global credential manager."""
    global _CREDENTIAL_MANAGER_INSTANCE
    if _CREDENTIAL_MANAGER_INSTANCE is None:
        _CREDENTIAL_MANAGER_INSTANCE = SecureCredentialManager()
    return _CREDENTIAL_MANAGER_INSTANCE
