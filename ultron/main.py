"""
ULTRON — Production Desktop Application & CLI Entrypoint
─────────────────────────────────────────────────────────────────────────────
Launches the sovereign real-time voice agent with streaming audio I/O,
Gemini Live bidirectional session, sub-50ms barge-in, local tool gateway,
secret-sanitizing logging, single-instance enforcement, and health diagnostics.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

# Ensure root workspace or package is on sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ultron.__version__ import __version__, __build_date__, __product_name__
from ultron.core.paths import ensure_runtime_directories, get_logs_dir
from ultron.core.config import get_config
from ultron.core.runtime import UltronRuntime
from ultron.core.logging_sanitizer import setup_logging
from ultron.core.single_instance import SingleInstanceLock
from ultron.core.startup import StartupManager
from ultron.core.lifecycle import LifecycleManager, LifecycleState
from ultron.diagnostics.system import print_health_report, print_diagnostics_report
from ultron.benchmark import run_performance_benchmark

logger = logging.getLogger("ultron.main")


async def run_live_agent(no_ui: bool = False, is_startup: bool = False, force_setup: bool = False):
    """Runs interactive live microphone session."""
    ensure_runtime_directories()
    lifecycle = LifecycleManager(LifecycleState.STARTING)
    startup_mgr = StartupManager()

    if is_startup and not startup_mgr.check_circuit_breaker():
        logger.critical("[ULTRON] Aborting launch: Startup circuit breaker is tripped due to previous repeated crashes.")
        print("\n[!] STARTUP CIRCUIT BREAKER ACTIVE: Aborting automatic launch to prevent crash loop.")
        return

    lifecycle.transition_to(LifecycleState.INITIALIZING, reason="Loading configuration and runtime")
    config = get_config()
    runtime = UltronRuntime(config)

    # 1. Initialize desktop presence overlay FIRST so UI is immediately visible on screen!
    presence = None
    if not no_ui:
        try:
            from ultron.presence.manager import PresenceManager
            presence = PresenceManager(runtime)
            presence.start(force_onboarding=force_setup)
        except Exception as e:
            logger.warning(f"Presence UI could not be started: {e}. Running in voice-only mode.")

    # 2. Check for GEMINI_API_KEY
    if not config.gemini_api_key:
        if no_ui:
            print("\n=======================================================")
            print(f"             {__product_name__} v{__version__} — FIRST-RUN SETUP             ")
            print("=======================================================")
            print(" GEMINI_API_KEY is required for real-time voice intelligence.")
            print(" Free Gemini API Key available at: https://aistudio.google.com/app/apikey")
            print("-------------------------------------------------------")
            try:
                if sys.stdin and sys.stdin.isatty():
                    entered_key = input(" Enter your Gemini API Key: ").strip()
                    if entered_key:
                        from ultron.core.credentials import get_credential_manager
                        get_credential_manager().set_api_key("GEMINI_API_KEY", entered_key)
                        config.gemini_api_key = entered_key
                        print("\n[OK] API key securely encrypted in Windows DPAPI store.\n")
                    else:
                        print("\n[!] Setup incomplete: GEMINI_API_KEY is required to launch ULTRON.")
                        input("\nPress Enter to exit...")
                        lifecycle.transition_to(LifecycleState.FAILED, reason="Missing GEMINI_API_KEY")
                        return
                else:
                    lifecycle.transition_to(LifecycleState.FAILED, reason="Missing GEMINI_API_KEY")
                    return
            except (EOFError, KeyboardInterrupt):
                lifecycle.transition_to(LifecycleState.FAILED, reason="Missing GEMINI_API_KEY")
                return
        else:
            print("\n=======================================================")
            print(f"             {__product_name__} v{__version__} — DESKTOP OVERLAY ACTIVE             ")
            print("=======================================================")
            print(" Desktop Presence Overlay is open at the top notch of your screen.")
            print(" Complete setup or configure your Gemini API Key to activate voice.")
            print("=======================================================\n")

    print(f" Build Date:  {__build_date__}")
    print(f" Model:       {config.model.model} (Voice: {config.model.voice_name})")
    print(f" Audio In:    {config.audio.input_sample_rate} Hz PCM16 Mono")
    print(f" Audio Out:   {config.audio.output_sample_rate} Hz PCM16 Mono")
    print(" Barge-in:    Active (Sub-50ms Playback Cancellation)")
    print(" Safety:      4-Tier Local Tool Gateway")
    print(" Status:      Listening. Speak naturally or press Ctrl+C to exit.")
    print("=======================================================\n")

    # Graceful signal handling
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _sig_handler():
        logger.info("Shutdown signal received.")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _sig_handler)
        except (NotImplementedError, RuntimeError):
            pass

    try:
        if config.gemini_api_key:
            await runtime.start()
            lifecycle.transition_to(LifecycleState.READY, reason="Runtime and audio started")
            lifecycle.transition_to(LifecycleState.RUNNING, reason="Listening for user speech")
            if is_startup:
                startup_mgr.record_successful_startup()
            print("\n>>> ULTRON ONLINE: Speak into your microphone... (Press Ctrl+C to stop)\n")
        else:
            print("\n>>> ULTRON DESKTOP ACTIVE: Waiting for onboarding / API key configuration...\n")

        while not stop_event.is_set():
            if not runtime.is_running:
                from ultron.core.credentials import get_credential_manager
                key = config.gemini_api_key or get_credential_manager().get_api_key("GEMINI_API_KEY")
                if key:
                    config.gemini_api_key = key
                    try:
                        await runtime.start()
                        lifecycle.transition_to(LifecycleState.RUNNING, reason="Listening for user speech")
                        print("\n>>> ULTRON ONLINE: Connected to Gemini Live voice stream.\n")
                    except Exception as ex:
                        logger.error(f"[ULTRON] Error starting runtime: {ex}")
            await asyncio.sleep(0.5)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    except Exception as ex:
        logger.error(f"[ULTRON] Fatal error during runtime execution: {ex}")
        lifecycle.transition_to(LifecycleState.FAILED, reason=str(ex))
        raise
    finally:
        lifecycle.transition_to(LifecycleState.STOPPING, reason="Initiating clean shutdown")
        print("\n[ULTRON] Shutting down audio streams and live session...")
        if presence:
            try:
                presence.stop()
            except Exception as e:
                logger.error(f"[ULTRON] Error stopping presence UI: {e}")
        try:
            await runtime.stop()
        except Exception as e:
            logger.error(f"[ULTRON] Error stopping runtime: {e}")
        lifecycle.transition_to(LifecycleState.STOPPED, reason="Clean shutdown completed")
        print("[ULTRON] Offline.\n")


def main():
    parser = argparse.ArgumentParser(description=f"{__product_name__} — Sovereign Realtime Multimodal AI Assistant")
    parser.add_argument("--version", action="version", version=f"{__product_name__} v{__version__} ({__build_date__})")
    parser.add_argument("--health", action="store_true", help="Run comprehensive system health check")
    parser.add_argument("--diagnostics", action="store_true", help="Output machine-readable diagnostics report")
    parser.add_argument("--benchmark", action="store_true", help="Run performance & latency benchmark")
    parser.add_argument("--no-ui", action="store_true", help="Run in headless / voice-only mode without desktop presence overlay")
    parser.add_argument("--startup", action="store_true", help="Indicates launch by Windows startup")
    parser.add_argument("--set-api-key", type=str, metavar="KEY", help="Securely store Gemini API key in Windows DPAPI store")
    parser.add_argument("--setup", "--configure", action="store_true", dest="setup", help="Open configuration and onboarding dropdown UI")
    parser.add_argument("--reset-config", action="store_true", help="Reset user configuration to clean install state")
    parser.add_argument("--enable-startup", action="store_true", help="Register application in Windows startup")
    parser.add_argument("--disable-startup", action="store_true", help="Unregister application from Windows startup")

    args = parser.parse_args()

    # Configure structured sanitized logging
    setup_logging()

    # 1. Health check CLI
    if args.health:
        sys.exit(print_health_report())

    # 2. Diagnostics CLI
    if args.diagnostics:
        sys.exit(print_diagnostics_report())

    # 3. Benchmark CLI
    if args.benchmark:
        run_performance_benchmark()
        return

    # 4. Credential configuration CLI
    if args.set_api_key:
        from ultron.core.credentials import get_credential_manager
        mgr = get_credential_manager()
        ok = mgr.set_api_key("GEMINI_API_KEY", args.set_api_key)
        if ok:
            print("\n[OK] GEMINI_API_KEY securely saved in Windows DPAPI encrypted store.\n")
            sys.exit(0)
        else:
            print("\n[ERROR] Failed to save credential in Windows DPAPI store.\n")
            sys.exit(1)

    # 5. Reset Config CLI
    if args.reset_config:
        from ultron.core.user_config import reset_user_config
        reset_user_config()
        print("\n[OK] User configuration reset to initial clean install state.\n")
        sys.exit(0)

    # 6. Startup configuration CLI
    if args.enable_startup:
        sm = StartupManager()
        ok = sm.enable_startup()
        if ok:
            print("\n[OK] ULTRON registered for Windows startup.\n")
            sys.exit(0)
        else:
            print("\n[ERROR] Failed to register Windows startup.\n")
            sys.exit(1)

    if args.disable_startup:
        sm = StartupManager()
        ok = sm.disable_startup()
        if ok:
            print("\n[OK] ULTRON unregistered from Windows startup.\n")
            sys.exit(0)
        else:
            print("\n[ERROR] Failed to unregister Windows startup.\n")
            sys.exit(1)

    # 7. Single-instance enforcement for live agent
    single_instance = SingleInstanceLock()
    if not single_instance.acquire():
        print(f"\n[!] {__product_name__} is already running in another window or background process.")
        sys.exit(0)

    try:
        asyncio.run(run_live_agent(no_ui=args.no_ui, is_startup=args.startup, force_setup=args.setup))
    except KeyboardInterrupt:
        print("\nExited.")
    except Exception as e:
        logger.critical(f"[ULTRON] Uncaught fatal error: {e}", exc_info=True)
        print(f"\n[FATAL ERROR] {e}")
        if sys.stdin and sys.stdin.isatty():
            input("\nPress Enter to exit...")
    finally:
        single_instance.release()


if __name__ == "__main__":
    main()
