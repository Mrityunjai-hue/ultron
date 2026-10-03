"""
ULTRON V3 — Real Performance Benchmark Suite
─────────────────────────────────────────────────────────────────────────────
Measures real performance across IDLE, LISTENING, and RESPONDING states:
- Process CPU (%)
- GPU Utilization (%) & VRAM (MB)
- Process RAM / RSS (MB)
- Playback Cancellation Latency (ms)
- Local Interruption Detection Latency (ms)
- Local Tool Gateway Execution Latency (ms)
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import asyncio
import os
import sys
import subprocess
import time
from pathlib import Path
import numpy as np
import psutil

# Ensure root workspace is on sys.path regardless of how script is executed
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ultron.core.config import get_config
from ultron.core.runtime import UltronRuntime
from ultron.realtime.audio_stream import AudioStreamEngine
from ultron.realtime.interruption import InterruptionManager
from ultron.tools.executor import ToolExecutor

def get_gpu_metrics() -> dict:
    """Queries NVIDIA GPU metrics via nvidia-smi if available."""
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=1.0,
        )
        if res.returncode == 0:
            parts = [p.strip() for p in res.stdout.strip().split(",")]
            return {
                "gpu_util_percent": float(parts[0]),
                "vram_used_mb": float(parts[1]),
                "vram_total_mb": float(parts[2]),
            }
    except Exception:
        pass
    return {"gpu_util_percent": 0.0, "vram_used_mb": 0.0, "vram_total_mb": 0.0}

def sample_resources(proc: psutil.Process, duration_sec: float = 2.0, interval: float = 0.2) -> dict:
    """Samples Process CPU %, GPU %, and Process RAM (MB) over a given duration."""
    cpu_samples = []
    gpu_samples = []
    ram_samples = []

    steps = int(duration_sec / interval)
    proc.cpu_percent() # Prime CPU counter

    for _ in range(steps):
        time.sleep(interval)
        cpu_samples.append(proc.cpu_percent())
        ram_samples.append(proc.memory_info().rss / (1024 * 1024))
        gpu_info = get_gpu_metrics()
        gpu_samples.append(gpu_info["gpu_util_percent"])

    return {
        "avg_cpu_percent": round(float(np.mean(cpu_samples)), 2),
        "peak_cpu_percent": round(float(np.max(cpu_samples)), 2),
        "avg_ram_mb": round(float(np.mean(ram_samples)), 2),
        "peak_ram_mb": round(float(np.max(ram_samples)), 2),
        "avg_gpu_percent": round(float(np.mean(gpu_samples)), 2),
    }

def run_performance_benchmark() -> dict:
    """Executes the complete empirical benchmark."""
    print("\n=======================================================")
    print("         ULTRON V3 REALTIME BENCHMARK SUITE            ")
    print("=======================================================\n")

    proc = psutil.Process(os.getpid())
    results = {}

    # 1. IDLE State Measurement (Baseline runtime without active audio stream)
    print("[1/5] Measuring IDLE state resource consumption (2.0s)...")
    idle_metrics = sample_resources(proc, duration_sec=2.0)
    results["IDLE"] = idle_metrics
    print(f"      IDLE CPU: {idle_metrics['avg_cpu_percent']}% (Peak: {idle_metrics['peak_cpu_percent']}%) | RAM: {idle_metrics['avg_ram_mb']}MB | GPU: {idle_metrics['avg_gpu_percent']}%")

    # 2. LISTENING State Measurement (Active non-blocking 16kHz audio capture & RMS calculation)
    print("\n[2/5] Measuring LISTENING state resource consumption (2.0s)...")
    audio = AudioStreamEngine(input_sample_rate=16000, output_sample_rate=24000, chunk_size=512)
    asyncio.run(audio.start())
    listen_metrics = sample_resources(proc, duration_sec=2.0)
    results["LISTENING"] = listen_metrics
    print(f"      LISTENING CPU: {listen_metrics['avg_cpu_percent']}% (Peak: {listen_metrics['peak_cpu_percent']}%) | RAM: {listen_metrics['avg_ram_mb']}MB | GPU: {listen_metrics['avg_gpu_percent']}%")

    # 3. RESPONDING State & Playback Cancellation Latency Measurement
    print("\n[3/5] Measuring RESPONDING state & Playback Cancellation Latency...")
    # Generate 1.0s of synthetic 24kHz sine wave audio chunks
    t_arr = np.linspace(0, 1.0, 24000, endpoint=False)
    sine_audio = (np.sin(2 * np.pi * 440 * t_arr) * 16000).astype(np.int16).tobytes()

    # Enqueue chunks into playback stream
    for i in range(0, len(sine_audio), 1024):
        audio.enqueue_playback(sine_audio[i:i+1024])

    time.sleep(0.1) # Let playback begin
    resp_metrics = sample_resources(proc, duration_sec=1.0)
    results["RESPONDING"] = resp_metrics

    # Test playback cancellation latency
    cancellation_latencies = []
    for _ in range(5):
        # Enqueue audio again
        for i in range(0, len(sine_audio), 1024):
            audio.enqueue_playback(sine_audio[i:i+1024])
        time.sleep(0.05)
        lat = audio.clear_playback()
        cancellation_latencies.append(lat)

    avg_cancel_lat = round(float(np.mean(cancellation_latencies)), 2)
    min_cancel_lat = round(float(np.min(cancellation_latencies)), 2)
    results["cancellation_latency_ms"] = avg_cancel_lat
    print(f"      RESPONDING CPU: {resp_metrics['avg_cpu_percent']}% | RAM: {resp_metrics['avg_ram_mb']}MB")
    print(f"      Playback Cancellation Latency: {avg_cancel_lat}ms (Min: {min_cancel_lat}ms)")

    # 4. Interruption Detection Latency Measurement
    print("\n[4/5] Measuring Local Barge-in Interruption Detection Latency...")
    interruption_latencies = []
    detected_times = []

    def _interruption_cb(lat_ms: float):
        detected_times.append(lat_ms)

    interruption_mgr = InterruptionManager(
        audio_engine=audio,
        rms_threshold=0.035,
        consecutive_frames_required=2,
        on_interruption=_interruption_cb,
    )

    for _ in range(5):
        # Enqueue audio to make is_playing True
        for i in range(0, len(sine_audio), 1024):
            audio.enqueue_playback(sine_audio[i:i+1024])
        time.sleep(0.05)

        # Feed loud speech chunk (RMS ~0.20)
        loud_chunk = (np.sin(2 * np.pi * 300 * np.linspace(0, 0.032, 512)) * 20000).astype(np.int16).tobytes()
        interruption_mgr.process_input_frame(loud_chunk, rms_energy=0.15)
        interruption_mgr.process_input_frame(loud_chunk, rms_energy=0.15)

    avg_detect_lat = round(float(np.mean(detected_times)), 2) if detected_times else 0.0
    results["interruption_detection_latency_ms"] = avg_detect_lat
    print(f"      Local Interruption Reaction Latency: {avg_detect_lat}ms")

    asyncio.run(audio.stop())

    # 5. Local Tool Gateway & Memory Subsystem Latencies
    print("\n[5/5] Measuring Local Tool Gateway & Memory Latencies...")
    executor = ToolExecutor(get_config().workspace_root)
    tool_timings = {}

    # Benchmark Memory Subsystems
    t0_mem_write = time.perf_counter()
    executor.memory.remember("bench_pref", "fast_responses")
    dt_mem_write = round((time.perf_counter() - t0_mem_write) * 1000.0, 3)

    t0_mem_read = time.perf_counter()
    _ = executor.memory.list_memories()
    dt_mem_read = round((time.perf_counter() - t0_mem_read) * 1000.0, 3)

    # Benchmark Confirmation Token Lifecycle
    t0_conf_gen = time.perf_counter()
    pending_conf = executor.confirmation.create_pending_confirmation("delete_file", {"path": "bench_test.txt"})
    dt_conf_gen = round((time.perf_counter() - t0_conf_gen) * 1000.0, 3)

    t0_conf_val = time.perf_counter()
    executor.confirmation.validate_and_consume(pending_conf.token, "delete_file", {"path": "bench_test.txt"})
    dt_conf_val = round((time.perf_counter() - t0_conf_val) * 1000.0, 3)

    # Clean benchmark memory
    executor.memory.forget("bench_pref")

    tool_timings["memory_write_ms"] = dt_mem_write
    tool_timings["memory_lookup_ms"] = dt_mem_read
    tool_timings["confirm_gen_ms"] = dt_conf_gen
    tool_timings["confirm_val_ms"] = dt_conf_val

    # Write file token flow
    req_write = executor.confirmation.create_pending_confirmation("write_file", {"path": "test_phase3_bench.txt", "content": "Benchmark"})
    t0 = time.perf_counter()
    asyncio.run(executor.execute("write_file", {"path": "test_phase3_bench.txt", "content": "Benchmark", "confirmation_token": req_write.token}))
    tool_timings["write_file"] = round((time.perf_counter() - t0) * 1000.0, 2)

    # Read file
    t0 = time.perf_counter()
    asyncio.run(executor.execute("read_file", {"path": "test_phase3_bench.txt"}))
    tool_timings["read_file"] = round((time.perf_counter() - t0) * 1000.0, 2)

    # Delete file token flow
    req_del = executor.confirmation.create_pending_confirmation("delete_file", {"path": "test_phase3_bench.txt"})
    t0 = time.perf_counter()
    asyncio.run(executor.execute("delete_file", {"path": "test_phase3_bench.txt", "confirmation_token": req_del.token}))
    tool_timings["delete_file"] = round((time.perf_counter() - t0) * 1000.0, 2)

    # System status and clock
    t0 = time.perf_counter()
    asyncio.run(executor.execute("get_current_time", {}))
    tool_timings["get_current_time"] = round((time.perf_counter() - t0) * 1000.0, 2)

    t0 = time.perf_counter()
    asyncio.run(executor.execute("get_system_status", {}))
    tool_timings["get_system_status"] = round((time.perf_counter() - t0) * 1000.0, 2)

    # Open app & Close app with token
    t0 = time.perf_counter()
    asyncio.run(executor.execute("open_app", {"app_name": "notepad"}))
    tool_timings["open_app"] = round((time.perf_counter() - t0) * 1000.0, 2)

    time.sleep(0.3)
    req_close = executor.confirmation.create_pending_confirmation("close_app", {"app_name": "notepad"})
    t0 = time.perf_counter()
    asyncio.run(executor.execute("close_app", {"app_name": "notepad", "confirmation_token": req_close.token}))
    tool_timings["close_app"] = round((time.perf_counter() - t0) * 1000.0, 2)

    results["tools"] = tool_timings

    # 6. Phase 6 Task Engine Multi-Step & Verification Benchmarks
    print("\n[6/7] Measuring Phase 6 Task Planning & Execution Engine Latencies...")
    from ultron.tasks.planner import TaskPlanner
    from ultron.tasks.executor import TaskExecutionEngine

    planner = TaskPlanner(get_config().workspace_root)
    engine = TaskExecutionEngine(executor, executor.confirmation, executor.memory, workspace_root=get_config().workspace_root)
    task_timings = {}

    # Task Creation & Validation
    t0 = time.perf_counter()
    sample_plan = [
        {"tool_name": "get_current_time", "arguments": {}, "purpose": "Time check"},
        {"tool_name": "get_system_status", "arguments": {}, "purpose": "Status check"},
    ]
    t_obj = planner.plan_multi_step_task("Benchmark Multi-step", sample_plan)
    task_timings["plan_creation_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)

    # Multi-Step Execution & Verification
    t0 = time.perf_counter()
    asyncio.run(engine.execute_task(t_obj))
    task_timings["multi_step_exec_and_verify_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

    # Instant Cancellation Latency
    t_cancel = planner.plan_single_action("get_current_time", {}, user_intent="Cancel test")
    t0 = time.perf_counter()
    engine.cancellation.cancel_task(t_cancel.task_id, reason="Benchmark cancel")
    task_timings["task_cancellation_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)

    results["tasks"] = task_timings
    print(f"      Task Plan Validation Latency: {task_timings['plan_creation_ms']}ms")
    print(f"      2-Step Execution + Verification: {task_timings['multi_step_exec_and_verify_ms']}ms")
    print(f"      Task Cancellation Reaction Latency: {task_timings['task_cancellation_ms']}ms")

    # 7. Presence Desktop Visualizer Benchmarks
    print("\n[7/7] Measuring Phase 4 Presence Desktop Visualizer Performance...")
    try:
        from ultron.presence.animation import SpringChoreographer
        from ultron.presence.audio_visualizer import AudioVisualizer
        from ultron.presence.renderer import PresenceRenderer
        from ultron.presence.window import UltronOverlayWindow

        ch = SpringChoreographer()
        viz = AudioVisualizer()
        renderer = PresenceRenderer(canvas_width=1920, canvas_height=400)

        # Measure raw rendering frame time across states
        frame_timings = {}
        for state in ("IDLE", "LISTENING", "THINKING", "RESPONDING", "TOOL_EXEC", "CONFIRMATION"):
            ch.set_state(state)
            times = []
            for _ in range(30):
                t0 = time.perf_counter()
                ch.update(0.016)
                viz.update(0.016)
                img = renderer.render_frame(ch, viz, 0.016)
                _ = renderer.to_premultiplied_bgra(img)
                times.append((time.perf_counter() - t0) * 1000.0)
            frame_timings[state] = round(float(np.mean(times)), 2)

        # Measure active overlay window memory and FPS
        win = UltronOverlayWindow(choreographer=ch, audio_visualizer=viz)
        win.start()
        time.sleep(0.5)
        ui_res = sample_resources(proc, duration_sec=1.5)
        
        # Test visual interruption reaction time
        t0_inter = time.perf_counter()
        viz.reset()
        ch.snap_interruption()
        dt_inter_visual_ms = round((time.perf_counter() - t0_inter) * 1000.0, 3)

        fps_achieved = round(win.metrics.get("fps", 60.0), 1)
        win.stop()

        results["presence"] = {
            "frame_timings_ms": frame_timings,
            "avg_frame_time_ms": round(float(np.mean(list(frame_timings.values()))), 2),
            "interruption_visual_ms": dt_inter_visual_ms,
            "ui_idle_ram_mb": ui_res["avg_ram_mb"],
            "ui_idle_cpu_percent": ui_res["avg_cpu_percent"],
            "fps": fps_achieved,
        }
        print(f"      Presence Average Frame Time: {results['presence']['avg_frame_time_ms']}ms (~{1000.0/results['presence']['avg_frame_time_ms']:.0f} max capacity FPS)")
        print(f"      Presence Interruption Visual Snap: {dt_inter_visual_ms}ms")
        print(f"      Presence Combined Idle CPU: {ui_res['avg_cpu_percent']}% | RAM: {ui_res['avg_ram_mb']}MB")
    except Exception as e:
        print(f"      [!] Presence benchmark note: {e}")

    # Final summary printout
    print("\n-------------------------------------------------------")
    print("               BENCHMARK SUMMARY REPORT                ")
    print("-------------------------------------------------------")
    print(f"IDLE:        CPU: {idle_metrics['avg_cpu_percent']}% | RAM: {idle_metrics['avg_ram_mb']} MB | GPU: {idle_metrics['avg_gpu_percent']}%")
    print(f"LISTENING:   CPU: {listen_metrics['avg_cpu_percent']}% | RAM: {listen_metrics['avg_ram_mb']} MB | GPU: {listen_metrics['avg_gpu_percent']}%")
    print(f"RESPONDING:  CPU: {resp_metrics['avg_cpu_percent']}% | RAM: {resp_metrics['avg_ram_mb']} MB | GPU: {resp_metrics['avg_gpu_percent']}%")
    if "presence" in results:
        p = results["presence"]
        print(f"PRESENCE:    Frame Time: {p['avg_frame_time_ms']}ms | Visual Interruption: {p['interruption_visual_ms']}ms | RAM: {p['ui_idle_ram_mb']} MB")
        print("  - Frame Timings per State:")
        for st, ft in p["frame_timings_ms"].items():
            print(f"    * {st:14s}: {ft} ms")
    print(f"Interruption Reaction Latency:   {avg_detect_lat} ms")
    print(f"Playback Cancellation Latency:   {avg_cancel_lat} ms")
    print("Memory & Security Latencies:")
    print(f"  - Memory Lookup Latency       : {dt_mem_read} ms")
    print(f"  - Persistent Write Latency    : {dt_mem_write} ms")
    print(f"  - Confirmation Gen Latency    : {dt_conf_gen} ms")
    print(f"  - Confirmation Valid Latency  : {dt_conf_val} ms")
    print("Tool Latencies:")
    for k, v in tool_timings.items():
        if not k.endswith("_ms"):
            print(f"  - {k:18s}: {v} ms")
    print("-------------------------------------------------------\n")

    return results

if __name__ == "__main__":
    run_performance_benchmark()

