"""
ULTRON Brain v2.0 — Local-First Sovereign LLM Pipeline
─────────────────────────────────────────────────────────────────────────────
Architectural Principles:
1. Local-First: Ollama (Hermes 4 14B) on http://localhost:11434 is primary.
2. Honest Offline State: If Ollama is unreachable, report OFFLINE explicitly.
   NEVER silently fall back to cloud providers.
3. Explicit Cloud Opt-in Only: Cloud models (Gemini) are used ONLY if
   explicitly configured (LLM_PROVIDER=gemini or config.brain.provider="gemini").
4. Native Tool Calling: Supports OpenAI/Ollama 0.3+ JSON schema tool definitions.
5. Sub-second Sentence Boundary Streaming: Dispatches clean, unformatted
   speech chunks to TTS on punctuation boundaries.
6. Zero Markdown Output: Strips markdown formatting to ensure clean audio.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import os
import sys
import asyncio
import logging
import json
import re
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any

import httpx

try:
    from laptop.brain.persona import build_ultron_system_prompt
    from laptop.core.states import ActivityState
except ImportError:
    from brain.persona import build_ultron_system_prompt
    from core.states import ActivityState

logger = logging.getLogger("ultron.brain.llm")

OFFLINE_NOTICE = (
    "Local neural substrate is offline. Ollama daemon is unreachable on port 11434. "
    "Start Ollama to activate cognitive processing."
)

def load_gemini_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                pass
    return key


class LLM:
    """Local-first streaming LLM with native tool calling and offline detection."""

    def __init__(self, config: dict):
        self.config = config
        brain_cfg = config.get("brain", {})

        # Provider: environment variable overrides config
        env_provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
        self.provider = env_provider or brain_cfg.get("provider", "ollama").lower()

        # Model: environment variable overrides config
        self.model = os.environ.get("LLM_MODEL", "") or brain_cfg.get("model", "hf.co/DevQuasar/NousResearch.Hermes-4-14B-GGUF:Q4_K_M")
        self.base_url = brain_cfg.get("ollama_url", "http://localhost:11434")
        self.max_tokens = brain_cfg.get("max_tokens", 256)
        self.temperature = brain_cfg.get("temperature", 0.72)

        # Generous timeout for local 14B neural inference on CPU/GPU
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(360.0, connect=10.0, read=360.0, write=30.0))
        self.gemini_key = load_gemini_key()

        # Last status telemetry
        self.last_state = ActivityState.IDLE
        self.is_offline = False

        if self.provider == "gemini":
            logger.warning("EXPLICIT CLOUD PROVIDER 'gemini' ACTIVATED. Telemetry will be sent to Google Cloud.")
        else:
            logger.info("[Brain] provider = ollama")
            logger.info(f"[Brain] model = {self.model}")
            logger.info("[Brain] inference = REAL")

    async def check_availability(self) -> bool:
        """Probes the configured brain to verify availability."""
        if self.provider == "gemini":
            return bool(self.gemini_key or load_gemini_key())

        try:
            resp = await self.client.get(f"{self.base_url}/api/tags", timeout=2.5)
            available = resp.status_code == 200
            self.is_offline = not available
            return available
        except Exception:
            self.is_offline = True
            return False

    async def generate_response(
        self,
        utterance: str,
        user: Optional[str] = None,
        confidence: float = 0.0,
        scene: str = "",
        relationship_mode: str = "STRANGER",
        interaction_count: int = 0,
        trust_score: float = 0.0,
        last_seen: str = "never",
        recent_history: Optional[List[Dict[str, Any]]] = None,
        known_facts: Optional[Dict[str, str]] = None,
        allowed_workspace: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_executor: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        on_sentence: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Main response generation entrypoint.
        Strictly respects local-first sovereignty.
        """
        system = build_ultron_system_prompt(
            user=user,
            confidence=confidence,
            scene=scene,
            relationship_mode=relationship_mode,
            interaction_count=interaction_count,
            trust_score=trust_score,
            last_seen=last_seen,
            recent_history=recent_history,
            known_facts=known_facts,
            allowed_workspace=allowed_workspace,
        )

        # ── 1. If explicit cloud provider 'gemini' is configured ─────────────
        if self.provider == "gemini":
            self.gemini_key = self.gemini_key or load_gemini_key()
            if not self.gemini_key:
                self.last_state = ActivityState.ERROR
                return "Gemini API key is not configured. Set GEMINI_API_KEY environment variable."
            try:
                self.last_state = ActivityState.THINKING
                return await self._stream_gemini(utterance, system, on_sentence)
            except Exception as e:
                logger.error(f"Gemini generation error: {e}")
                self.last_state = ActivityState.ERROR
                return f"Cloud inference fault: {e}"

        # ── 2. Local-first Ollama generation ─────────────────────────────────
        try:
            self.last_state = ActivityState.THINKING
            response = await self._stream_ollama(
                utterance,
                system,
                tools=tools,
                tool_executor=tool_executor,
                on_sentence=on_sentence,
            )
            self.last_state = ActivityState.RESPONDING
            self.is_offline = False
            return response
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"Local Ollama daemon unreachable: {e}")
            self.last_state = ActivityState.OFFLINE
            self.is_offline = True

            # Emit offline notice cleanly to TTS if callback provided
            if on_sentence:
                on_sentence(OFFLINE_NOTICE)

            return OFFLINE_NOTICE
        except Exception as e:
            logger.error(f"Local brain execution exception: {e}")
            self.last_state = ActivityState.ERROR
            error_msg = f"Neural processing error: {e}"
            if on_sentence:
                on_sentence(error_msg)
            return error_msg

    async def _stream_ollama(
        self,
        utterance: str,
        system: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_executor: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        on_sentence: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Processes request with local Ollama daemon, supporting structured tool loops."""
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": utterance},
        ]

        # If tools are defined, check whether Hermes decides to call a tool
        if tools:
            payload: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "stream": False,
                "keep_alive": "60m",
                "options": {
                    "num_predict": self.max_tokens,
                    "temperature": self.temperature,
                },
            }

            resp = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=360.0,
            )
            if resp.status_code != 200:
                body = resp.text
                raise RuntimeError(f"Ollama returned HTTP {resp.status_code}: {body}")

            data = resp.json()
            msg = data.get("message", {})
            tool_calls = msg.get("tool_calls", [])

            # Tool decision received from Hermes
            if tool_calls and tool_executor:
                messages.append(msg)
                for tool_call in tool_calls:
                    fn = tool_call.get("function", {})
                    fn_name = fn.get("name", "")
                    fn_args = fn.get("arguments", {})
                    call_id = tool_call.get("id", "call_1")

                    logger.info(f"[Brain] Structured tool reasoning decision: {fn_name}({fn_args})")
                    tool_result = await tool_executor(fn_name, fn_args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps(tool_result),
                    })

                # Request final natural-language synthesis from Hermes with tool result
                followup_payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "keep_alive": "60m",
                    "options": {
                        "num_predict": self.max_tokens,
                        "temperature": self.temperature,
                    },
                }

                full_response = ""
                current_clause = ""
                async with self.client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=followup_payload,
                    timeout=360.0,
                ) as f_resp:
                    if f_resp.status_code != 200:
                        f_body = await f_resp.aread()
                        raise RuntimeError(f"Ollama returned HTTP {f_resp.status_code}: {f_body.decode('utf-8', errors='ignore')}")

                    async for line in f_resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            tok = chunk.get("message", {}).get("content", "")
                            if tok:
                                full_response += tok
                                current_clause += tok
                                if re.search(r'[.!?\n]\s*$', current_clause) and len(current_clause.strip()) > 8:
                                    sentence = self._clean_speech_clause(current_clause)
                                    current_clause = ""
                                    if sentence and on_sentence:
                                        on_sentence(sentence)
                        except Exception:
                            pass

                if current_clause.strip():
                    rem = self._clean_speech_clause(current_clause)
                    if rem and on_sentence:
                        on_sentence(rem)

                return self._clean_speech_clause(full_response)

            # If no tool was chosen by Hermes, return direct response
            direct_content = msg.get("content", "")
            cleaned = self._clean_speech_clause(direct_content)
            if cleaned and on_sentence:
                on_sentence(cleaned)
            return cleaned

        # Direct streaming response when no tools provided
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "keep_alive": "60m",
            "options": {
                "num_predict": self.max_tokens,
                "temperature": self.temperature,
            },
        }

        full_response = ""
        current_clause = ""

        async with self.client.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=360.0,
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise RuntimeError(f"Ollama returned HTTP {resp.status_code}: {body.decode('utf-8', errors='ignore')}")

            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    msg = chunk.get("message", {})
                    token = msg.get("content", "")

                    if token:
                        full_response += token
                        current_clause += token

                        if re.search(r'[.!?\n]\s*$', current_clause) and len(current_clause.strip()) > 8:
                            trimmed = current_clause.strip()
                            if not re.search(r'\b(e\.g|i\.e|vs|v2\.0|dr|mr|ms)\.$', trimmed, re.IGNORECASE):
                                sentence = self._clean_speech_clause(current_clause)
                                current_clause = ""
                                if sentence and on_sentence:
                                    on_sentence(sentence)
                except Exception:
                    pass

            if current_clause.strip():
                remainder = self._clean_speech_clause(current_clause)
                if remainder and on_sentence:
                    on_sentence(remainder)

        return self._clean_speech_clause(full_response)

    async def _stream_gemini(
        self,
        utterance: str,
        system: str,
        on_sentence: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Explicit opt-in Google Gemini streaming."""
        import google.generativeai as genai

        genai.configure(api_key=self.gemini_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system,
        )

        def _generate():
            return model.generate_content(utterance, stream=True)

        stream = await asyncio.to_thread(_generate)
        full_text = ""
        current_clause = ""

        for chunk in stream:
            token = chunk.text
            if token:
                full_text += token
                current_clause += token
                if re.search(r'[.!?\n]\s*$', current_clause) and len(current_clause.strip()) > 8:
                    sentence = self._clean_speech_clause(current_clause)
                    current_clause = ""
                    if sentence and on_sentence:
                        on_sentence(sentence)

        if current_clause.strip():
            rem = self._clean_speech_clause(current_clause)
            if rem and on_sentence:
                on_sentence(rem)

        return self._clean_speech_clause(full_text)

    def _clean_speech_clause(self, text: str) -> str:
        """Removes markdown artefacts and non-speech characters so voice is natural for TTS."""
        if not text:
            return ""
        # Remove emojis and high surrogate characters
        t = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        # Remove bold, italics, code blocks, headers, bullet points
        t = re.sub(r'[*_#`~>\[\]\(\)]', '', t)
        t = re.sub(r'^\s*[-•]\s*', '', t, flags=re.MULTILINE)
        t = re.sub(r'\s+', ' ', t)
        return t.strip()

    async def close(self):
        await self.client.aclose()
