"""
ULTRON V3 — Optical Presence Renderer (Concept A: Singularity Crease)
─────────────────────────────────────────────────────────────────────────────
Implementation of Concept A: "The Singularity Crease"
A single, radically minimal horizontal tension horizon of concentrated plasma
energy trapped in an obsidian top-bezel capsule.

Visual Architecture:
- Obsidian Glass Capsule with top shoulder fillets attaching to screen bezel.
- The Singularity Crease: A razor-sharp, zero-radius incandescent laser core
  bleeding into deep electric violet and cold indigo atmospheric plasma glow.
- Parametrically morphs through all operational states (IDLE, HOVER, LISTENING,
  THINKING, SPEAKING, INTERRUPTED, TOOL_EXEC, TOOL_COMPLETE, CONFIRMATION, RETRACTED).
- 2x Supersampled software renderer → Lanczos downsample → Premultiplied BGRA.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import math
import os
import time
from typing import Dict, Any, Optional, Tuple, List
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ultron.presence.animation import SpringChoreographer
from ultron.presence.audio_visualizer import AudioVisualizer

# ─── Color System ────────────────────────────────────────────────────────────
CLR_VOID       = (4, 4, 8, 255)        # 100% Solid Obsidian — zero transparency
CLR_WHITE      = (255, 255, 255, 255)  # Incandescent white laser core
CLR_VIOLET     = (130, 45, 250, 255)   # Electric violet — primary plasma aura
CLR_INDIGO     = (70, 25, 180, 255)    # Deep cold indigo — atmospheric boundary
CLR_LAVENDER   = (195, 140, 255, 255)  # Vibrant lavender — plasma body
CLR_AMBER      = (245, 155, 25, 255)   # Security amber — warm precision
CLR_AMBER_BG   = (28, 18, 26, 255)     # Solid security button fill
CLR_EMERALD    = (16, 215, 135, 255)   # Success emerald — crisp mint
CLR_TXT_MAIN   = (242, 246, 255, 255)  # Pure off-white — primary text
CLR_TXT_MUTE   = (135, 150, 172, 255)  # Muted slate — secondary text
CLR_BORDER_SUB = (255, 255, 255, 70)   # Glass border


# ─── Font Discovery ──────────────────────────────────────────────────────────

def _load_fonts() -> dict:
    """Loads system fonts at 2x point sizes for sub-pixel antialiasing."""
    def first_existing(*paths):
        for p in paths:
            if os.path.exists(p):
                return p
    sb = first_existing("C:/Windows/Fonts/segoeuib.ttf",
                        "C:/Windows/Fonts/SegUIVar.ttf",
                        "C:/Windows/Fonts/arialbd.ttf") or "arialbd.ttf"
    sr = first_existing("C:/Windows/Fonts/segoeui.ttf",
                        "C:/Windows/Fonts/SegUIVar.ttf",
                        "C:/Windows/Fonts/arial.ttf") or "arial.ttf"
    sm = first_existing("C:/Windows/Fonts/CascadiaCode.ttf",
                        "C:/Windows/Fonts/consola.ttf",
                        "C:/Windows/Fonts/lucon.ttf") or "consola.ttf"

    def tf(path, size):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()

    return {
        "d_20b":   tf(sb, 40),   # display 20pt bold  (2x = 40pt)
        "d_18b":   tf(sb, 36),   # display 18pt bold  (2x = 36pt)
        "d_16b":   tf(sb, 32),   # display 16pt bold
        "d_14b":   tf(sb, 28),   # headline 14pt bold
        "d_13b":   tf(sb, 26),   # sub-headline 13pt bold
        "d_12b":   tf(sb, 24),   # sub-headline 12pt bold
        "b_13b":   tf(sb, 26),   # button 13pt semibold
        "b_12b":   tf(sb, 24),   # button 12pt semibold
        "b_11b":   tf(sb, 22),   # button 11pt semibold
        "r_13":    tf(sr, 26),   # regular 13pt
        "r_12":    tf(sr, 24),   # regular 12pt
        "r_11":    tf(sr, 22),   # regular 11pt
        "r_10":    tf(sr, 20),   # regular 10pt
        "m_11":    tf(sm, 22),   # mono 11pt
        "m_10":    tf(sm, 20),   # mono 10pt
        "m_9":     tf(sm, 18),   # mono 9pt
        "eye_10b": tf(sb, 20),   # eyebrow 10pt semibold
        "tag_9b":  tf(sb, 18),   # state label 9pt bold tracking
    }


FONTS = _load_fonts()


def _fmt_tool_label(tool_name: str) -> str:
    """Converts raw tool IDs to clean semantic labels."""
    t = tool_name.strip().upper()
    table = {
        "APP:OPEN": "APP · OPEN", "APP_OPEN": "APP · OPEN",
        "APP:RUN":  "APP · RUN",  "APP_RUN":  "APP · RUN",
        "FILE:READ": "FILE · READ", "FILE:DELETE": "FILE · DELETE",
        "FILE:WRITE": "FILE · WRITE", "SYS:STATUS": "SYS · STATUS",
        "DELETE_FILE": "FILE · DELETE",
    }
    for k, v in table.items():
        if k in t:
            return v
    parts = t.replace(":", " · ").replace("_", " ").split()
    if len(parts) >= 2:
        return f"{parts[0]} · {' '.join(parts[1:])}"
    return f"ACTION · {t}"


# ─── Main Renderer ────────────────────────────────────────────────────────────

class PresenceRenderer:
    """
    Renders the Concept A Singularity Crease presence UI at 2x resolution,
    then Lanczos-downsamples to the final window size.
    """

    def __init__(self, canvas_width: int = 640, canvas_height: int = 540):
        self.canvas_width  = canvas_width
        self.canvas_height = canvas_height
        self.scale   = 2.0
        self.buffer_w = int(canvas_width  * self.scale)
        self.buffer_h = int(canvas_height * self.scale)

        self._phase      = 0.0   # slow ambient clock (~1.2 rad/s)
        self._phase_fast = 0.0   # fast dynamic clock (~4.5 rad/s)

        self.tool_info:  Dict[str, Any] = {}
        self.vault_info: Dict[str, Any] = {}
        self.onboarding_controller = None

    # ─── Context setters ─────────────────────────────────────────────────

    def set_onboarding_controller(self, controller):
        self.onboarding_controller = controller

    def set_tool_context(self, tool_name: str, target: str,
                         status: str = "running", progress: float = 0.5):
        self.tool_info = {"tool_name": tool_name, "target": target,
                          "status": status, "progress": progress}

    def set_vault_context(self, action: str, target: str, message: str = ""):
        self.vault_info = {"action": action.upper(), "target": target,
                            "message": message}

    # ─── Render entry ────────────────────────────────────────────────────

    def render_frame(
        self,
        choreographer: SpringChoreographer,
        audio_viz: AudioVisualizer,
        dt: float,
    ) -> Image.Image:
        """Returns an RGBA frame at canvas resolution, ready for BGRA conversion."""
        self._phase      += dt * 1.2
        self._phase_fast += dt * 4.5

        ch = choreographer
        nw = ch.size.x + ch.hover_lift.current
        nh = ch.size.y
        if nw <= 4 or nh <= 2:
            return Image.new("RGBA", (self.canvas_width, self.canvas_height), (0, 0, 0, 0))

        S  = self.scale
        cx  = self.canvas_width / 2.0
        lx  = cx - nw / 2.0
        rx  = lx + nw
        ty  = 0.0
        by  = ty + nh
        r   = min(ch.corner_radius.current, nh / 2.0)
        flare_r = min(24.0, max(8.0, r * 0.9))
        is_expanded = (by - ty) > 85.0
        taper_x = 0.0 if is_expanded else (6.0 if (by - ty) > 20.0 else 0.0)

        # Build scaled notch polygon vertices
        pts_raw = self._build_notch_polygon(lx, ty, rx, by, r, flare_r, taper_x)
        scaled  = [(p[0] * S, p[1] * S) for p in pts_raw]

        # 1. Base Layer: 100% Solid Obsidian Notch Body
        notch_base = Image.new("RGBA", (self.buffer_w, self.buffer_h), (0, 0, 0, 0))
        draw_base = ImageDraw.Draw(notch_base)
        draw_base.polygon(scaled, fill=CLR_VOID)

        # 2. Content Layer: Crease, Plasma Glows, Text, Icons, Buttons
        content_layer = Image.new("RGBA", (self.buffer_w, self.buffer_h), (0, 0, 0, 0))
        draw_content = ImageDraw.Draw(content_layer)

        # Perimeter specular edge / rim glow
        self._draw_rim_glow(draw_content, scaled, ch, S)

        # Singularity Crease Optical Entity
        sig_y = (ty + 22.0) if is_expanded else (ty + nh / 2.0)
        self._draw_singularity_crease(draw_content, cx, sig_y, ch, dt, S, is_compact=is_expanded)

        # Contextual surface content with Bouncy Pop-up Kinetics
        onb_a   = ch.onboarding_alpha.current
        pod_a   = ch.action_pod_alpha.current
        vault_a = ch.vault_alpha.current
        cont_a  = ch.content_alpha.current

        if onb_a > 0.03 and nh > 85.0:
            self._draw_onboarding(draw_content, lx, ty, nw, nh, onb_a, cont_a, ch, S)
        elif pod_a > 0.03 and nh > 85.0:
            self._draw_tool_pod(draw_content, lx, ty, nw, nh, pod_a, cont_a, ch, S)
        elif vault_a > 0.03 and nh > 85.0:
            self._draw_vault(draw_content, lx, ty, nw, nh, vault_a, cont_a, ch, S)

        # 3. Alpha Composite content OVER the solid base (Keeps solid alpha=255)
        notch_base.alpha_composite(content_layer)

        # 4. Fast Downsample 2x → 1x for crisp antialiasing (Bilinear is 40x faster than Lanczos)
        final = notch_base.resize((self.canvas_width, self.canvas_height), Image.Resampling.BILINEAR)
        return final

    # ─── Notch body & Rim Glow ───────────────────────────────────────────

    def _draw_rim_glow(
        self,
        draw: ImageDraw.ImageDraw,
        scaled: List[Tuple[float, float]],
        ch: SpringChoreographer,
        S: float,
    ):
        """Perimeter specular edge / rim glow drawn on content layer."""
        state = ch.current_state_name
        spec_a = ch.specular_rim.current

        if state == "CONFIRMATION":
            # Amber security rim contour on bottom and sides
            glow_w = max(1, int(4.0 * S))
            draw.line(scaled[:-1], fill=(CLR_AMBER[0], CLR_AMBER[1], CLR_AMBER[2], 75), width=glow_w)
            draw.line(scaled[:-1], fill=(CLR_AMBER[0], CLR_AMBER[1], CLR_AMBER[2], 230), width=max(1, int(1.6 * S)))
            # Shoulder lavender rim light
            sh_left = scaled[:18]
            sh_right = scaled[36:54]
            draw.line(sh_left, fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], 180), width=max(1, int(1.4 * S)))
            draw.line(sh_right, fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], 180), width=max(1, int(1.4 * S)))
        elif spec_a > 0.002:
            # Elegant cold-white / lavender shoulder highlight
            rim_a = min(255, int(spec_a * 480))
            rim_col = (215, 205, 250, rim_a)
            draw.line(scaled[:-1], fill=rim_col, width=max(1, int(1.4 * S)))

    def _build_notch_polygon(
        self,
        lx: float, ty: float, rx: float, by: float,
        r: float, flare_r: float, taper_x: float = 0.0,
    ) -> List[Tuple[float, float]]:
        """Builds notch polygon vertices with top shoulder fillets and rounded corners."""
        pts = []

        # Left concave shoulder flare (curves from top edge down into left notch wall)
        for i in range(18):
            t = i / 17.0
            theta = t * math.pi * 0.5
            x = (lx - flare_r) + flare_r * math.sin(theta)
            y = flare_r - flare_r * math.cos(theta)
            pts.append((x, y))

        # Bottom-left rounded corner (with subtle inward taper)
        bot_lx = lx + taper_x
        for i in range(18):
            t = i / 17.0
            angle = math.pi + t * math.pi * 0.5
            x = (bot_lx + r) + r * math.cos(angle)
            y = (by - r) - r * math.sin(angle)
            pts.append((x, y))

        # Bottom-right rounded corner (with subtle inward taper)
        bot_rx = rx - taper_x
        for i in range(18):
            t = i / 17.0
            angle = math.pi * 1.5 + t * math.pi * 0.5
            x = (bot_rx - r) + r * math.cos(angle)
            y = (by - r) - r * math.sin(angle)
            pts.append((x, y))

        # Right concave shoulder flare (curves from right notch wall up into top edge)
        for i in range(18):
            t = (1.0 - i / 17.0)
            theta = t * math.pi * 0.5
            x = (rx + flare_r) - flare_r * math.sin(theta)
            y = flare_r - flare_r * math.cos(theta)
            pts.append((x, y))

        # Close along top screen bezel
        pts.append((rx + flare_r, 0.0))
        pts.append((lx - flare_r, 0.0))
        return pts

    # ─── Concept A: The Singularity Crease ─────────────────────────────────

    def _draw_singularity_crease(
        self,
        draw: ImageDraw.ImageDraw,
        cx: float, cy: float,
        ch: SpringChoreographer,
        dt: float, S: float,
        is_compact: bool = False,
    ):
        """
        Concept A Core Entity:
        A razor-sharp, zero-radius horizontal plasma crease under magnetic tension.
        Features a pure white-hot center flare, radiant lavender-violet plasma diffusion,
        and kinetic spring flare transitions.
        """
        state   = ch.current_state_name
        w_int   = ch.white_core.current
        v_int   = ch.violet_aura.current
        flare   = ch.crease_flare.current
        w_nrg   = ch.wave_energy.current
        res     = ch._audio_resonance
        gaze_x  = ch.gaze_x.current
        gaze_y  = ch.gaze_y.current
        ph      = self._phase
        ph_f    = self._phase_fast

        ccx = (cx + gaze_x) * S
        ccy = (cy + gaze_y) * S

        # Base horizontal span modulated by spring
        base_span = ch.crease_span.current if not is_compact else (ch.crease_span.current * 0.75)
        span_px = base_span * (1.0 + 0.12 * (flare - 1.0))
        half_span = (span_px * 0.5) * S

        N = 120
        pts = []

        # State-dependent kinetic modulation
        for i in range(N):
            u = (i / (N - 1)) * 2.0 - 1.0  # u in [-1.0, 1.0]
            # Smooth magnetic compression envelope: (1 - u^2)^0.65
            env = max(0.0, 1.0 - u * u) ** 0.65

            # Transition ripple packet
            wave_trans = w_nrg * 2.5 * math.sin(8.0 * math.pi * u - ph_f * 2.0) * math.exp(-2.5 * abs(u))

            if state == "IDLE":
                # Subtle sub-pixel breathing
                breath = 0.85 + 0.15 * math.sin(ph * 0.8)
                y_mod = (0.6 * math.sin(math.pi * u) * breath) + wave_trans
            elif state == "HOVER":
                # Responsive tension lift
                y_mod = (1.0 * math.sin(math.pi * u)) + wave_trans
            elif state == "LISTENING":
                # Acoustic vertical compression & micro-wave ripples
                y_mod = ((2.2 * math.sin(2.0 * math.pi * u - ph * 1.5) + res * 3.8 * math.sin(4.0 * math.pi * u)) * env) + wave_trans
            elif state == "THINKING":
                # High-frequency quantum shimmer
                y_mod = ((1.8 * math.sin(6.0 * math.pi * u + ph_f * 1.2) + 0.9 * math.cos(10.0 * math.pi * u - ph_f * 0.8)) * env) + wave_trans
            elif state == "RESPONDING":
                # Fluid voice-driven plasma undulation
                y_mod = ((3.6 * math.sin(1.5 * math.pi * u - ph * 2.0) + res * 6.5 * math.sin(3.0 * math.pi * u + ph * 1.5)) * env) + wave_trans
            elif state == "INTERRUPTED":
                y_mod = (2.8 * math.sin(4.0 * math.pi * u) * env) + wave_trans
            else:
                y_mod = (0.4 * math.sin(math.pi * u)) + wave_trans

            x = ccx + u * half_span
            y = ccy + y_mod * S
            pts.append((x, y, u))

        # Effective optical intensity with flare surge
        eff_w = min(1.0, w_int * (0.8 + 0.2 * flare))
        eff_v = min(1.0, v_int * (0.8 + 0.2 * flare))

        # 1. Atmospheric Diffuse Plasma Halo (Violet/Indigo field)
        self._render_crease_halo(draw, ccx, ccy, half_span, eff_v, flare, state, S, is_compact)

        # 2. Multi-layered Plasma Dispersion & Laser Core
        self._render_crease_layers(draw, pts, eff_w, eff_v, flare, state, S)

        # 3. Central Singularity Specular Burst (Diamond Lens Flare)
        self._render_crease_burst(draw, ccx, ccy, eff_w, eff_v, flare, state, S, is_compact)

    def _render_crease_halo(
        self,
        draw: ImageDraw.ImageDraw,
        cx: float, cy: float,
        half_span: float,
        v_int: float,
        flare: float,
        state: str,
        S: float,
        is_compact: bool,
    ):
        """Volumetric diffuse plasma bloom spreading horizontally behind the crease."""
        va = max(0, min(255, int(v_int * 255)))
        if va <= 0:
            return

        if state == "CONFIRMATION":
            c_aura = (CLR_AMBER[0], CLR_AMBER[1], CLR_AMBER[2])
            c_deep = (180, 95, 20)
        elif state == "TOOL_COMPLETE":
            c_aura = (CLR_EMERALD[0], CLR_EMERALD[1], CLR_EMERALD[2])
            c_deep = (10, 140, 85)
        else:
            c_aura = (CLR_VIOLET[0], CLR_VIOLET[1], CLR_VIOLET[2])
            c_deep = (CLR_INDIGO[0], CLR_INDIGO[1], CLR_INDIGO[2])

        # Outer diffuse elliptical plasma cloud
        gw = half_span * (1.1 + 0.15 * (flare - 1.0))
        gh = (14.0 if is_compact else 22.0) * S * (1.0 + 0.2 * (flare - 1.0))
        draw.ellipse([cx - gw, cy - gh, cx + gw, cy + gh],
                     fill=(*c_deep, max(0, min(255, int(va * 0.18)))))

        # Inner vibrant plasma glow core
        mw = half_span * 0.75
        mh = (8.0 if is_compact else 12.0) * S * (1.0 + 0.15 * (flare - 1.0))
        draw.ellipse([cx - mw, cy - mh, cx + mw, cy + mh],
                     fill=(*c_aura, max(0, min(255, int(va * 0.32)))))

    def _render_crease_layers(
        self,
        draw: ImageDraw.ImageDraw,
        pts: list,
        w_int: float, v_int: float,
        flare: float,
        state: str, S: float,
    ):
        """Renders the segmented plasma crease with variable thickness and optical tapering."""
        if len(pts) < 2:
            return

        wa = max(0, min(255, int(w_int * 255)))
        va = max(0, min(255, int(v_int * 255)))

        if state == "CONFIRMATION":
            aura_col  = (220, 130, 30)
            body_col  = (250, 180, 70)
            trans_col = (255, 225, 150)
        elif state == "TOOL_COMPLETE":
            aura_col  = (10, 160, 95)
            body_col  = (80, 225, 165)
            trans_col = (175, 245, 215)
        else:
            aura_col  = (CLR_VIOLET[0],   CLR_VIOLET[1],   CLR_VIOLET[2])
            body_col  = (CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2])
            trans_col = (235, 215, 255)

        flare_thick = 1.0 + 0.25 * (flare - 1.0)

        for k in range(len(pts) - 1):
            p0 = pts[k]
            p1 = pts[k + 1]
            u_avg = (p0[2] + p1[2]) * 0.5
            taper = max(0.08, (1.0 - u_avg * u_avg) ** 0.5)

            seg = [(p0[0], p0[1]), (p1[0], p1[1])]

            # Layer 1: Outer Plasma Dispersion
            if va > 0:
                gw = max(1, int(11.0 * S * taper * flare_thick))
                ga = max(0, min(255, int(va * 0.22 * taper)))
                draw.line(seg, fill=(*aura_col, ga), width=gw)

            # Layer 2: Mid Luminous Body
            if va > 0:
                mw = max(1, int(5.2 * S * taper * flare_thick))
                ma = max(0, min(255, int(va * 0.85 * taper)))
                draw.line(seg, fill=(*body_col, ma), width=mw)

            # Layer 3: Transition Lavender-to-White
            if va > 0:
                tw = max(1, int(3.0 * S * taper))
                ta = max(0, min(255, int(va * 0.95 * taper)))
                draw.line(seg, fill=(*trans_col, ta), width=tw)

            # Layer 4: Laser Pure White Core
            if wa > 0:
                cw = max(1, int(1.6 * S * taper))
                ca = max(0, min(255, int(wa * (0.35 + 0.65 * taper))))
                draw.line(seg, fill=(255, 255, 255, ca), width=cw)

    def _render_crease_burst(
        self,
        draw: ImageDraw.ImageDraw,
        cx: float, cy: float,
        w_int: float, v_int: float,
        flare: float,
        state: str, S: float,
        is_compact: bool,
    ):
        """Brilliant incandescent singularity point with horizontal lens flare burst."""
        wa = max(0, min(255, int(w_int * 255)))
        va = max(0, min(255, int(v_int * 255)))

        if state == "CONFIRMATION":
            flare_c = (CLR_AMBER[0], CLR_AMBER[1], CLR_AMBER[2])
        elif state == "TOOL_COMPLETE":
            flare_c = (CLR_EMERALD[0], CLR_EMERALD[1], CLR_EMERALD[2])
        else:
            flare_c = (CLR_VIOLET[0], CLR_VIOLET[1], CLR_VIOLET[2])

        fl_scale = 1.0 + 0.45 * (flare - 1.0)

        # 1. Soft radial center glow
        if va > 0:
            cr = (10.0 if is_compact else 16.0) * S * fl_scale
            draw.ellipse([cx - cr, cy - cr * 0.45, cx + cr, cy + cr * 0.45],
                         fill=(*flare_c, max(0, min(255, int(va * 0.45)))))

        # 2. Horizontal diamond lens streak
        if wa > 0:
            hw = (18.0 if is_compact else 28.0) * S * fl_scale
            hh = (2.6 if is_compact else 3.8) * S
            draw.polygon([(cx - hw, cy), (cx, cy - hh), (cx + hw, cy), (cx, cy + hh)],
                         fill=(255, 255, 255, max(0, min(255, int(wa * 0.95)))))

            # Vertical micro-spike
            vw = 2.4 * S
            vh = (6.0 if is_compact else 9.0) * S * fl_scale
            draw.polygon([(cx - vw, cy), (cx, cy - vh), (cx + vw, cy), (cx, cy + vh)],
                         fill=(255, 255, 255, max(0, min(255, int(wa * 0.80)))))

        # 3. Pure white specular point
        if wa > 0:
            pr = (1.8 if is_compact else 2.6) * S
            draw.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=(255, 255, 255, wa))

    # ─── Tool Execution & Complete Surface ───────────────────────────────

    def _draw_tool_pod(
        self,
        draw: ImageDraw.ImageDraw,
        lx: float, ty: float, w: float, nh: float,
        pod_alpha: float, content_alpha: float,
        ch: SpringChoreographer, S: float,
    ):
        """Tool execution surface (Spacious Action Panel with elastic pop-up scale)."""
        a = min(1.0, pod_alpha) * min(1.0, content_alpha)
        if a < 0.03:
            return

        c_scale = ch.content_scale.current
        c_off_y = ch.content_offset_y.current
        i_scale = ch.icon_bounce.current

        ia = lambda v: max(0, min(255, int(v)))

        tool_raw = self.tool_info.get("tool_name", "APP:OPEN")
        target   = self.tool_info.get("target",   "Google Chrome")
        status   = self.tool_info.get("status",   "running")

        # Parse app name and tech ID from target string
        if "(" in target and ")" in target:
            app_name = target[:target.index("(")].strip()
            tech_id  = target[target.index("(") + 1 : target.index(")")]
        else:
            app_name = target
            parts = target.split()
            last = parts[-1] if parts else ""
            if len(parts) > 1 and last.lower() not in app_name.lower():
                tech_id = last
            else:
                tech_id = ""

        if len(app_name) > 28:
            app_name = app_name[:28] + "\u2026"
        if len(tech_id) > 24:
            tech_id = tech_id[:24]

        # Apply spring vertical entrance offset
        content_y = (ty + 54.0 + c_off_y) * S
        left_x    = (lx + 46.0) * S

        # 1. Eyebrow label (APP · OPEN)
        eyebrow = _fmt_tool_label(tool_raw)
        draw.text((left_x, content_y),
                  eyebrow,
                  fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(220 * a)),
                  font=FONTS["eye_10b"])

        # 2. App name — dominant white headline
        draw.text((left_x, content_y + 20.0 * S),
                  app_name,
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(252 * a)),
                  font=FONTS["d_20b"])

        # 3. Tech ID — muted mono
        if tech_id:
            draw.text((left_x, content_y + 56.0 * S),
                      tech_id,
                      fill=(CLR_TXT_MUTE[0], CLR_TXT_MUTE[1], CLR_TXT_MUTE[2], ia(185 * a)),
                      font=FONTS["m_10"])

        # 4. Vertical divider
        div_x = (lx + w - 142.0) * S
        draw.line([(div_x, content_y + 6.0 * S), (div_x, content_y + 72.0 * S)],
                  fill=(255, 255, 255, ia(24 * a)),
                  width=max(1, int(1.0 * S)))

        # 5. Status area (right column with elastic bounce)
        right_cx = (lx + w - 72.0) * S
        status_y = content_y + 24.0 * S

        if status == "complete":
            # Emerald circle with elastic checkmark bounce
            circle_r = 14.0 * S * i_scale
            draw.ellipse(
                [right_cx - circle_r, status_y - circle_r, right_cx + circle_r, status_y + circle_r],
                outline=(CLR_EMERALD[0], CLR_EMERALD[1], CLR_EMERALD[2], ia(240 * a)),
                width=max(1, int(1.8 * S)),
            )
            # Checkmark ✓ inside
            chk_pts = [
                (right_cx - 7.0 * S * i_scale, status_y - 1.0 * S),
                (right_cx - 2.0 * S * i_scale, status_y + 4.0 * S * i_scale),
                (right_cx + 7.0 * S * i_scale, status_y - 5.0 * S * i_scale),
            ]
            draw.line(chk_pts, fill=(CLR_EMERALD[0], CLR_EMERALD[1], CLR_EMERALD[2], ia(255 * a)), width=max(1, int(2.4 * S)))

            # "Opened" label below
            try:
                bb = FONTS["b_11b"].getbbox("Opened")
                tw = bb[2] - bb[0]
            except Exception:
                tw = 60
            draw.text((right_cx - tw // 2, content_y + 54.0 * S),
                      "Opened",
                      fill=(CLR_EMERALD[0], CLR_EMERALD[1], CLR_EMERALD[2], ia(245 * a)),
                      font=FONTS["b_11b"])
        else:
            # Sleek Rotary Arc Spinner with dynamic comet glow
            ph = self._phase_fast
            spin_r = 13.0 * S
            # Outer faint ring
            draw.ellipse(
                [right_cx - spin_r, status_y - spin_r, right_cx + spin_r, status_y + spin_r],
                outline=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(45 * a)),
                width=max(1, int(2.2 * S)),
            )
            # Glowing arc segment
            arc_pts = []
            arc_span = math.pi * 1.3
            for k in range(24):
                t = k / 23.0
                theta = ph * 2.0 + t * arc_span
                ax = right_cx + spin_r * math.cos(theta)
                ay = status_y + spin_r * math.sin(theta)
                arc_pts.append((ax, ay))
            draw.line(arc_pts, fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(240 * a)), width=max(1, int(2.4 * S)))

            # "Opening..." text
            try:
                bb = FONTS["m_10"].getbbox("Opening...")
                tw = bb[2] - bb[0]
            except Exception:
                tw = 70
            draw.text((right_cx - tw // 2, content_y + 54.0 * S),
                      "Opening...",
                      fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(210 * a)),
                      font=FONTS["m_10"])

    # ─── Security Confirmation Vault ─────────────────────────────────────

    def _draw_vault(
        self,
        draw: ImageDraw.ImageDraw,
        lx: float, ty: float, w: float, nh: float,
        vault_alpha: float, content_alpha: float,
        ch: SpringChoreographer, S: float,
    ):
        """Security authorization surface (with elastic card popup and bouncy buttons)."""
        a = min(1.0, vault_alpha) * min(1.0, content_alpha)
        if a < 0.03:
            return

        c_scale = ch.content_scale.current
        c_off_y = ch.content_offset_y.current
        b_scale = ch.button_scale.current
        i_bounce = ch.icon_bounce.current

        ia   = lambda v: max(0, min(255, int(v)))
        vcx  = (lx + w / 2.0) * S
        top  = (ty + 44.0 + c_off_y) * S

        action = self.vault_info.get("action", "DELETE_FILE")
        target = self.vault_info.get("target", "build/artifacts/cache.db")

        if "DELETE" in action:
            phrase = "Delete this file?"
        elif "WRITE" in action or "CREATE" in action:
            phrase = "Create or modify this file?"
        elif "EXECUTE" in action or "RUN" in action:
            phrase = f"Execute: {action.replace('_', ' ').lower()}?"
        else:
            phrase = f"{action.replace('_', ' ').title()}?"
        if len(phrase) > 40:
            phrase = phrase[:40] + "\u2026"
        if len(target) > 46:
            target = "\u2026" + target[-46:]

        # 1. Eyebrow: SECURITY · CONFIRM (amber)
        eyebrow = "SECURITY \u00b7 CONFIRM"
        try:
            bb = FONTS["eye_10b"].getbbox(eyebrow)
            ew = bb[2] - bb[0]
        except Exception:
            ew = 140
        draw.text((vcx - ew // 2, top),
                  eyebrow,
                  fill=(CLR_AMBER[0], CLR_AMBER[1], CLR_AMBER[2], ia(245 * a)),
                  font=FONTS["eye_10b"])

        # 2. Warning Triangle Icon ⚠️ with elastic bounce
        tri_cx = (lx + 68.0) * S
        tri_cy = top + 42.0 * S
        self._render_warning_triangle(draw, tri_cx, tri_cy, ia(240 * a), i_bounce, S)

        # 3. Question headline & Target path (aligned beside triangle)
        text_lx = (lx + 106.0) * S
        draw.text((text_lx, top + 22.0 * S),
                  phrase,
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(252 * a)),
                  font=FONTS["d_20b"])

        draw.text((text_lx, top + 58.0 * S),
                  target,
                  fill=(CLR_TXT_MUTE[0], CLR_TXT_MUTE[1], CLR_TXT_MUTE[2], ia(185 * a)),
                  font=FONTS["m_10"])

        # 4. Interactive Buttons with Bouncy Spring Scale
        btn_top = (ty + 134.0 + c_off_y) * S
        btn_w   = 154.0 * S
        btn_h   = 42.0 * S
        gap     = 18.0 * S
        btn_r   = int(10.0 * S)

        # Allow button (primary — solid amber-obsidian base with warm glow)
        al_lx = vcx - btn_w - gap * 0.5
        self._draw_button(draw, al_lx, btn_top, btn_w, btn_h, btn_r,
                          fill=(CLR_AMBER_BG[0], CLR_AMBER_BG[1], CLR_AMBER_BG[2], ia(255 * a)),
                          border=(CLR_AMBER[0], CLR_AMBER[1], CLR_AMBER[2], ia(195 * a)),
                          label="Allow",
                          shortcut="\u21b5 Enter",
                          label_col=(250, 252, 255, ia(255 * a)),
                          shortcut_col=(CLR_AMBER[0], CLR_AMBER[1], CLR_AMBER[2], ia(240 * a)),
                          scale=b_scale,
                          S=S)

        # Dismiss button (secondary — solid obsidian base with glass border)
        dis_lx = vcx + gap * 0.5
        self._draw_button(draw, dis_lx, btn_top, btn_w, btn_h, btn_r,
                          fill=(16, 16, 24, ia(255 * a)),
                          border=(255, 255, 255, ia(60 * a)),
                          label="Dismiss",
                          shortcut="Esc",
                          label_col=(205, 215, 230, ia(235 * a)),
                          shortcut_col=(120, 135, 155, ia(195 * a)),
                          scale=b_scale,
                          S=S)

    def _render_warning_triangle(
        self,
        draw: ImageDraw.ImageDraw,
        cx: float, cy: float,
        alpha: int,
        bounce_scale: float,
        S: float,
    ):
        """Vector glowing amber warning triangle icon ⚠️ with elastic scale."""
        tw = 16.0 * S * bounce_scale
        th = 15.0 * S * bounce_scale
        top_pt = (cx, cy - th)
        bot_l  = (cx - tw, cy + th * 0.85)
        bot_r  = (cx + tw, cy + th * 0.85)

        # Amber outer glow
        draw.polygon([top_pt, bot_l, bot_r], fill=(CLR_AMBER[0], CLR_AMBER[1], CLR_AMBER[2], int(alpha * 0.22)))
        # Triangle border
        draw.line([top_pt, bot_l, bot_r, top_pt], fill=(CLR_AMBER[0], CLR_AMBER[1], CLR_AMBER[2], alpha), width=max(1, int(2.2 * S)))

        # Exclamation point inside
        ex_top = cy - th * 0.35
        ex_bot = cy + th * 0.25
        draw.line([(cx, ex_top), (cx, ex_bot)], fill=(CLR_AMBER[0], CLR_AMBER[1], CLR_AMBER[2], alpha), width=max(1, int(2.0 * S)))
        # Dot
        dr = 1.2 * S * bounce_scale
        draw.ellipse([cx - dr, cy + th * 0.55 - dr, cx + dr, cy + th * 0.55 + dr], fill=(CLR_AMBER[0], CLR_AMBER[1], CLR_AMBER[2], alpha))

    def _draw_button(
        self,
        draw: ImageDraw.ImageDraw,
        bx: float, by: float, bw: float, bh: float, br: int,
        fill: tuple, border: tuple,
        label: str, shortcut: str,
        label_col: tuple, shortcut_col: tuple,
        scale: float,
        S: float,
    ):
        """ULTRON button: rounded rect with center-based elastic spring scale."""
        if abs(scale - 1.0) > 0.001:
            bcx = bx + bw * 0.5
            bcy = by + bh * 0.5
            bw = bw * scale
            bh = bh * scale
            bx = bcx - bw * 0.5
            by = bcy - bh * 0.5

        draw.rounded_rectangle(
            [bx, by, bx + bw, by + bh],
            radius=br, fill=fill, outline=border,
            width=max(1, int(1.6 * S)),
        )
        # Label — left-padded
        label_y = by + (bh - 26.0 * S) / 2.0
        draw.text((bx + 22.0 * S, label_y), label, fill=label_col, font=FONTS["b_13b"])
        # Shortcut — right-padded
        try:
            bb = FONTS["m_9"].getbbox(shortcut)
            sw = bb[2] - bb[0]
        except Exception:
            sw = 38
        sc_y = by + (bh - 18.0 * S) / 2.0
        draw.text((bx + bw - sw - 18.0 * S, sc_y),
                  shortcut, fill=shortcut_col, font=FONTS["m_9"])

    # ─── Onboarding Surface & Step Renderers ─────────────────────────────

    def _draw_onboarding(
        self,
        draw: ImageDraw.ImageDraw,
        lx: float, ty: float, w: float, nh: float,
        onb_alpha: float, content_alpha: float,
        ch: SpringChoreographer, S: float,
    ):
        """Renders the 6-stage liquid onboarding experience on the obsidian surface."""
        a = min(1.0, onb_alpha) * min(1.0, content_alpha)
        if a < 0.03:
            return

        ctrl = self.onboarding_controller
        step = ctrl.current_step if ctrl else 1
        total_steps = ctrl.total_steps if ctrl else 6
        step_alpha = min(1.0, a * (ctrl.content_alpha.current if ctrl else 1.0))
        step_off_y = (ctrl.content_offset_y.current if ctrl else 0.0) * S
        b_scale = ch.button_scale.current

        ia = lambda v: max(0, min(255, int(v)))
        vcx = (lx + w / 2.0) * S
        content_left = (lx + 40.0) * S
        content_right = (lx + w - 40.0) * S

        # 1. Step Indicator Track at top
        track_y = (ty + 42.0) * S
        self._draw_step_track(draw, vcx, track_y, step, total_steps, a, S)

        # 2. Main Step Content Container (with smooth spring transition displacement)
        body_top = (ty + 74.0) * S + step_off_y

        if step == 1:
            self._draw_step_01_owner(draw, content_left, content_right, body_top, ctrl, step_alpha, S)
        elif step == 2:
            self._draw_step_02_addressing(draw, content_left, content_right, body_top, ctrl, step_alpha, S)
        elif step == 3:
            self._draw_step_03_identity(draw, content_left, content_right, body_top, ctrl, step_alpha, S)
        elif step == 4:
            self._draw_step_04_interaction(draw, content_left, content_right, body_top, ctrl, step_alpha, S)
        elif step == 5:
            self._draw_step_05_privacy(draw, content_left, content_right, body_top, ctrl, step_alpha, S)
        elif step == 6:
            self._draw_step_06_startup(draw, content_left, content_right, body_top, ctrl, step_alpha, S)

        # 3. Validation error message if active
        if ctrl and ctrl.validation_error and step_alpha > 0.1:
            err_y = (ty + nh - 84.0) * S
            draw.text(
                (content_left + 4.0 * S, err_y),
                f"⚠ {ctrl.validation_error}",
                fill=(CLR_AMBER[0], CLR_AMBER[1], CLR_AMBER[2], ia(240 * step_alpha)),
                font=FONTS["m_10"],
            )

        # 4. Bottom Navigation Buttons
        btn_top = (ty + nh - 60.0) * S
        btn_h = 42.0 * S
        btn_r = int(10.0 * S)

        # Back button (Steps 2..6)
        if step > 1:
            back_w = 120.0 * S
            self._draw_button(
                draw, content_left, btn_top, back_w, btn_h, btn_r,
                fill=(16, 16, 24, ia(255 * a)),
                border=(255, 255, 255, ia(50 * a)),
                label="Back",
                shortcut="Esc",
                label_col=(205, 215, 230, ia(235 * a)),
                shortcut_col=(120, 135, 155, ia(195 * a)),
                scale=b_scale,
                S=S,
            )

        # Next / Finish button
        next_w = (176.0 if step == total_steps else 154.0) * S
        next_lx = content_right - next_w
        if step == total_steps:
            # Radiant Finish button (Amber/Lavender Primary)
            self._draw_button(
                draw, next_lx, btn_top, next_w, btn_h, btn_r,
                fill=(38, 22, 54, ia(255 * a)),
                border=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(230 * a)),
                label="Finish Setup",
                shortcut="\u21b5 Enter",
                label_col=(255, 255, 255, ia(255 * a)),
                shortcut_col=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(240 * a)),
                scale=b_scale,
                S=S,
            )
        else:
            # Primary Continue button
            self._draw_button(
                draw, next_lx, btn_top, next_w, btn_h, btn_r,
                fill=(24, 20, 36, ia(255 * a)),
                border=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(195 * a)),
                label="Continue",
                shortcut="\u21b5 Enter",
                label_col=(250, 252, 255, ia(255 * a)),
                shortcut_col=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(240 * a)),
                scale=b_scale,
                S=S,
            )

    def _draw_step_track(
        self,
        draw: ImageDraw.ImageDraw,
        cx: float, cy: float,
        current_step: int, total_steps: int,
        alpha: float, S: float,
    ):
        """Renders the sleek minimalist 6-step progress pills."""
        ia = lambda v: max(0, min(255, int(v)))
        pill_w = 34.0 * S
        pill_h = 7.0 * S
        gap = 8.0 * S
        total_w = total_steps * pill_w + (total_steps - 1) * gap
        start_x = cx - total_w * 0.5

        for i in range(1, total_steps + 1):
            px = start_x + (i - 1) * (pill_w + gap)
            if i < current_step:
                # Completed step: solid soft lavender/emerald
                draw.rounded_rectangle(
                    [px, cy, px + pill_w, cy + pill_h],
                    radius=int(3.5 * S),
                    fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(180 * alpha)),
                )
            elif i == current_step:
                # Active step: incandescent glowing white-lavender
                draw.rounded_rectangle(
                    [px - 2.0 * S, cy - 1.0 * S, px + pill_w + 2.0 * S, cy + pill_h + 1.0 * S],
                    radius=int(4.5 * S),
                    fill=(CLR_VIOLET[0], CLR_VIOLET[1], CLR_VIOLET[2], ia(80 * alpha)),
                )
                draw.rounded_rectangle(
                    [px, cy, px + pill_w, cy + pill_h],
                    radius=int(3.5 * S),
                    fill=(255, 255, 255, ia(255 * alpha)),
                )
            else:
                # Inactive upcoming step: muted dark track
                draw.rounded_rectangle(
                    [px, cy, px + pill_w, cy + pill_h],
                    radius=int(3.5 * S),
                    fill=(255, 255, 255, ia(28 * alpha)),
                )

    def _draw_step_01_owner(
        self,
        draw: ImageDraw.ImageDraw,
        left_x: float, right_x: float, top_y: float,
        ctrl: Any, a: float, S: float,
    ):
        """STEP 01 — OWNER SETUP."""
        ia = lambda v: max(0, min(255, int(v)))
        w = right_x - left_x

        # 1. Eyebrow
        draw.text((left_x, top_y), "STEP 01 / 06 \u00b7 OWNER",
                  fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(220 * a)),
                  font=FONTS["eye_10b"])

        # 2. Headline
        draw.text((left_x, top_y + 18.0 * S), "Let's set up ULTRON.",
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(255 * a)),
                  font=FONTS["d_20b"])

        # 3. Subtitle
        draw.text((left_x, top_y + 48.0 * S), "Before we begin, tell me who I'm working with.",
                  fill=(CLR_TXT_MUTE[0], CLR_TXT_MUTE[1], CLR_TXT_MUTE[2], ia(190 * a)),
                  font=FONTS["r_12"])

        # 4. Preferred Name Field
        f1_y = top_y + 82.0 * S
        f_h = 46.0 * S
        is_f1_active = (ctrl.active_field == "owner_name") if ctrl else True
        self._draw_input_box(
            draw=draw, x=left_x, y=f1_y, w=w, h=f_h,
            label="PREFERRED NAME *",
            text=ctrl.owner_name if ctrl else "",
            placeholder="e.g. Mrityunjai",
            is_active=is_f1_active,
            show_cursor=(ctrl.cursor_visible if ctrl else False) and is_f1_active,
            cursor_pos=ctrl.cursor_pos if ctrl else 0,
            alpha=a, S=S,
        )

        # 5. Pronunciation Hint Field
        f2_y = top_y + 160.0 * S
        is_f2_active = (ctrl.active_field == "pronunciation_hint") if ctrl else False
        self._draw_input_box(
            draw=draw, x=left_x, y=f2_y, w=w, h=f_h,
            label="PRONUNCIATION HINT (OPTIONAL)",
            text=ctrl.pronunciation_hint if ctrl else "",
            placeholder="e.g. Mree-tyoon-jai",
            is_active=is_f2_active,
            show_cursor=(ctrl.cursor_visible if ctrl else False) and is_f2_active,
            cursor_pos=ctrl.cursor_pos if ctrl else 0,
            alpha=a, S=S,
        )

    def _draw_step_02_addressing(
        self,
        draw: ImageDraw.ImageDraw,
        left_x: float, right_x: float, top_y: float,
        ctrl: Any, a: float, S: float,
    ):
        """STEP 02 — ADDRESSING."""
        ia = lambda v: max(0, min(255, int(v)))
        w = right_x - left_x
        owner = (ctrl.owner_name.strip() if ctrl and ctrl.owner_name else "Your Name")

        # Eyebrow
        draw.text((left_x, top_y), "STEP 02 / 06 \u00b7 ADDRESSING",
                  fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(220 * a)),
                  font=FONTS["eye_10b"])

        # Headline
        draw.text((left_x, top_y + 18.0 * S), "What should I call you?",
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(255 * a)),
                  font=FONTS["d_20b"])

        # Subtitle
        draw.text((left_x, top_y + 48.0 * S), "Choose how ULTRON will address you in conversation.",
                  fill=(CLR_TXT_MUTE[0], CLR_TXT_MUTE[1], CLR_TXT_MUTE[2], ia(190 * a)),
                  font=FONTS["r_12"])

        # Option 1: Use Preferred Name
        c1_y = top_y + 78.0 * S
        c_h = 56.0 * S
        is_opt1 = (ctrl.addressing_mode == "preferred") if ctrl else True
        self._draw_option_card(
            draw=draw, x=left_x, y=c1_y, w=w, h=c_h,
            title=f"Use Preferred Name (\"{owner}\")",
            subtitle="ULTRON will address you by your preferred first name.",
            is_selected=is_opt1,
            alpha=a, S=S,
        )

        # Option 2: Custom Form of Address
        c2_y = top_y + 144.0 * S
        is_opt2 = (ctrl.addressing_mode == "custom") if ctrl else False
        self._draw_option_card(
            draw=draw, x=left_x, y=c2_y, w=w, h=c_h,
            title="Custom Form of Address",
            subtitle="e.g. \"Mr.\", \"Commander\", \"Dr.\", or specific honorific",
            is_selected=is_opt2,
            alpha=a, S=S,
        )

        # Custom Address Input (when option 2 is selected)
        if is_opt2:
            inp_y = top_y + 210.0 * S
            self._draw_input_box(
                draw=draw, x=left_x, y=inp_y, w=w, h=44.0 * S,
                label="CUSTOM FORM OF ADDRESS *",
                text=ctrl.custom_address if ctrl else "",
                placeholder="e.g. Mr.",
                is_active=(ctrl.active_field == "custom_address") if ctrl else True,
                show_cursor=(ctrl.cursor_visible if ctrl else False),
                cursor_pos=ctrl.cursor_pos if ctrl else 0,
                alpha=a, S=S,
            )

    def _draw_step_03_identity(
        self,
        draw: ImageDraw.ImageDraw,
        left_x: float, right_x: float, top_y: float,
        ctrl: Any, a: float, S: float,
    ):
        """STEP 03 — ULTRON IDENTITY."""
        ia = lambda v: max(0, min(255, int(v)))
        w = right_x - left_x

        # Eyebrow
        draw.text((left_x, top_y), "STEP 03 / 06 \u00b7 ULTRON IDENTITY",
                  fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(220 * a)),
                  font=FONTS["eye_10b"])

        # Headline
        draw.text((left_x, top_y + 18.0 * S), "What would you like to call me?",
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(255 * a)),
                  font=FONTS["d_20b"])

        # Subtitle
        draw.text((left_x, top_y + 48.0 * S), "Keep ULTRON or designate a custom assistant name.",
                  fill=(CLR_TXT_MUTE[0], CLR_TXT_MUTE[1], CLR_TXT_MUTE[2], ia(190 * a)),
                  font=FONTS["r_12"])

        # Option 1: ULTRON (Recommended)
        c1_y = top_y + 78.0 * S
        c_h = 56.0 * S
        is_opt1 = (ctrl.identity_mode == "ultron") if ctrl else True
        self._draw_option_card(
            draw=draw, x=left_x, y=c1_y, w=w, h=c_h,
            title="ULTRON (Recommended)",
            subtitle="Sovereign, calculating multimodal desktop AI entity.",
            is_selected=is_opt1,
            alpha=a, S=S,
        )

        # Option 2: Custom Name
        c2_y = top_y + 144.0 * S
        is_opt2 = (ctrl.identity_mode == "custom") if ctrl else False
        self._draw_option_card(
            draw=draw, x=left_x, y=c2_y, w=w, h=c_h,
            title="Custom Assistant Name",
            subtitle="Designate a custom name for your AI assistant.",
            is_selected=is_opt2,
            alpha=a, S=S,
        )

        # Custom Name Input (when option 2 is selected)
        if is_opt2:
            inp_y = top_y + 210.0 * S
            self._draw_input_box(
                draw=draw, x=left_x, y=inp_y, w=w, h=44.0 * S,
                label="CUSTOM ASSISTANT NAME *",
                text=ctrl.custom_assistant_name if ctrl else "",
                placeholder="e.g. Jarvis, Friday, Nova",
                is_active=(ctrl.active_field == "custom_assistant_name") if ctrl else True,
                show_cursor=(ctrl.cursor_visible if ctrl else False),
                cursor_pos=ctrl.cursor_pos if ctrl else 0,
                alpha=a, S=S,
            )

    def _draw_step_04_interaction(
        self,
        draw: ImageDraw.ImageDraw,
        left_x: float, right_x: float, top_y: float,
        ctrl: Any, a: float, S: float,
    ):
        """STEP 04 — INTERACTION & VOICE PREFERENCES."""
        ia = lambda v: max(0, min(255, int(v)))
        w = right_x - left_x
        sel_voice = ctrl.voice_name if ctrl else "Puck"
        sel_style = ctrl.response_style if ctrl else "Concise & Authoritative"

        # Eyebrow
        draw.text((left_x, top_y), "STEP 04 / 06 \u00b7 INTERACTION & VOICE",
                  fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(220 * a)),
                  font=FONTS["eye_10b"])

        # Headline
        draw.text((left_x, top_y + 18.0 * S), "Interaction & Voice",
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(255 * a)),
                  font=FONTS["d_20b"])

        # Section 1: Voice Persona (Row 1 & 2)
        draw.text((left_x, top_y + 50.0 * S), "GEMINI LIVE VOICE PERSONA",
                  fill=(CLR_TXT_MUTE[0], CLR_TXT_MUTE[1], CLR_TXT_MUTE[2], ia(180 * a)),
                  font=FONTS["tag_9b"])

        # Row 1 (Puck, Charon, Aoede)
        v_top1 = top_y + 68.0 * S
        pill_w3 = (w - 20.0 * S) / 3.0
        p_h = 38.0 * S

        self._draw_voice_pill(draw, left_x, v_top1, pill_w3, p_h, "Puck", "Clear & Direct", sel_voice == "Puck", a, S)
        self._draw_voice_pill(draw, left_x + pill_w3 + 10.0 * S, v_top1, pill_w3, p_h, "Charon", "Deep & Strong", sel_voice == "Charon", a, S)
        self._draw_voice_pill(draw, left_x + (pill_w3 + 10.0 * S) * 2, v_top1, pill_w3, p_h, "Aoede", "Warm & Precise", sel_voice == "Aoede", a, S)

        # Row 2 (Fenrir, Kore)
        v_top2 = top_y + 114.0 * S
        pill_w2 = (w - 10.0 * S) / 2.0
        self._draw_voice_pill(draw, left_x, v_top2, pill_w2, p_h, "Fenrir", "Dynamic & Bold", sel_voice == "Fenrir", a, S)
        self._draw_voice_pill(draw, left_x + pill_w2 + 10.0 * S, v_top2, pill_w2, p_h, "Kore", "Calm & Focused", sel_voice == "Kore", a, S)

        # Section 2: Conversational Style
        draw.text((left_x, top_y + 164.0 * S), "CONVERSATIONAL RESPONSE STYLE",
                  fill=(CLR_TXT_MUTE[0], CLR_TXT_MUTE[1], CLR_TXT_MUTE[2], ia(180 * a)),
                  font=FONTS["tag_9b"])

        s_top1 = top_y + 182.0 * S
        self._draw_style_pill(draw, left_x, s_top1, w, 36.0 * S, "Concise & Authoritative (Default)", sel_style.startswith("Concise"), a, S)
        s_top2 = top_y + 224.0 * S
        self._draw_style_pill(draw, left_x, s_top2, w, 36.0 * S, "Analytical & Detailed", sel_style.startswith("Analytical"), a, S)

    def _draw_step_05_privacy(
        self,
        draw: ImageDraw.ImageDraw,
        left_x: float, right_x: float, top_y: float,
        ctrl: Any, a: float, S: float,
    ):
        """STEP 05 — LOCAL PRIVACY & MEMORY."""
        ia = lambda v: max(0, min(255, int(v)))
        w = right_x - left_x

        # Eyebrow
        draw.text((left_x, top_y), "STEP 05 / 06 \u00b7 PRIVACY & MEMORY",
                  fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(220 * a)),
                  font=FONTS["eye_10b"])

        # Headline
        draw.text((left_x, top_y + 18.0 * S), "Local Privacy & Memory",
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(255 * a)),
                  font=FONTS["d_20b"])

        # Subtitle
        draw.text((left_x, top_y + 48.0 * S), "ULTRON can remember information you explicitly choose to keep.",
                  fill=(CLR_TXT_MUTE[0], CLR_TXT_MUTE[1], CLR_TXT_MUTE[2], ia(190 * a)),
                  font=FONTS["r_12"])

        # Privacy Architecture Card
        card_y = top_y + 76.0 * S
        card_h = 108.0 * S
        draw.rounded_rectangle(
            [left_x, card_y, left_x + w, card_y + card_h],
            radius=int(10.0 * S),
            fill=(10, 10, 18, ia(255 * a)),
            outline=(255, 255, 255, ia(35 * a)),
            width=max(1, int(1.2 * S)),
        )

        # Bullet 1: Local Storage
        b1_y = card_y + 14.0 * S
        draw.text((left_x + 18.0 * S, b1_y), "\u2022  Local Storage: Conversational memory and task state are kept strictly local.",
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(235 * a)),
                  font=FONTS["r_11"])

        # Bullet 2: Audio Privacy
        b2_y = card_y + 42.0 * S
        draw.text((left_x + 18.0 * S, b2_y), "\u2022  Audio Privacy: Raw microphone audio is streamed in-memory and never saved.",
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(235 * a)),
                  font=FONTS["r_11"])

        # Bullet 3: Sovereign Security
        b3_y = card_y + 70.0 * S
        draw.text((left_x + 18.0 * S, b3_y), "\u2022  Sovereign Security: Cloud AI by Gemini \u00b7 Local safety controls remain authoritative.",
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(235 * a)),
                  font=FONTS["r_11"])

        # Interactive Checkbox Card
        chk_y = top_y + 196.0 * S
        chk_h = 54.0 * S
        allow_mem = ctrl.allow_memory if ctrl else True
        self._draw_checkbox_card(
            draw=draw, x=left_x, y=chk_y, w=w, h=chk_h,
            title="Allow ULTRON to remember things I explicitly ask it to remember",
            is_checked=allow_mem,
            alpha=a, S=S,
        )

    def _draw_step_06_startup(
        self,
        draw: ImageDraw.ImageDraw,
        left_x: float, right_x: float, top_y: float,
        ctrl: Any, a: float, S: float,
    ):
        """STEP 06 — WINDOWS STARTUP & READY."""
        ia = lambda v: max(0, min(255, int(v)))
        w = right_x - left_x
        start_win = ctrl.start_with_windows if ctrl else False

        # Eyebrow
        draw.text((left_x, top_y), "STEP 06 / 06 \u00b7 READY",
                  fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(220 * a)),
                  font=FONTS["eye_10b"])

        # Headline
        draw.text((left_x, top_y + 18.0 * S), "Windows Startup",
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(255 * a)),
                  font=FONTS["d_20b"])

        # Subtitle
        draw.text((left_x, top_y + 48.0 * S), "Should ULTRON be ready when Windows starts?",
                  fill=(CLR_TXT_MUTE[0], CLR_TXT_MUTE[1], CLR_TXT_MUTE[2], ia(190 * a)),
                  font=FONTS["r_12"])

        # Interactive Checkbox Card
        chk_y = top_y + 82.0 * S
        chk_h = 56.0 * S
        self._draw_checkbox_card(
            draw=draw, x=left_x, y=chk_y, w=w, h=chk_h,
            title="Start ULTRON automatically with Windows",
            is_checked=start_win,
            alpha=a, S=S,
        )

        # Ready confirmation banner
        ready_y = top_y + 154.0 * S
        ready_h = 64.0 * S
        draw.rounded_rectangle(
            [left_x, ready_y, left_x + w, ready_y + ready_h],
            radius=int(10.0 * S),
            fill=(18, 14, 28, ia(255 * a)),
            outline=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(90 * a)),
            width=max(1, int(1.4 * S)),
        )

        draw.text((left_x + 18.0 * S, ready_y + 14.0 * S), "READY TO INITIALIZE",
                  fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(240 * a)),
                  font=FONTS["tag_9b"])
        draw.text((left_x + 18.0 * S, ready_y + 34.0 * S), "Click Finish Setup to finalize configuration and collapse into top notch.",
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(245 * a)),
                  font=FONTS["r_11"])

    # ─── UI Component Helpers ────────────────────────────────────────────

    def _draw_input_box(
        self,
        draw: ImageDraw.ImageDraw,
        x: float, y: float, w: float, h: float,
        label: str, text: str, placeholder: str,
        is_active: bool, show_cursor: bool, cursor_pos: int,
        alpha: float, S: float,
    ):
        """Obsidian liquid input field with glowing active focus border and blinking caret."""
        ia = lambda v: max(0, min(255, int(v)))

        # Label above field
        draw.text((x, y - 18.0 * S), label,
                  fill=(CLR_TXT_MUTE[0], CLR_TXT_MUTE[1], CLR_TXT_MUTE[2], ia(180 * alpha)),
                  font=FONTS["tag_9b"])

        # Input box body
        bg_col = (12, 12, 20, ia(255 * alpha))
        if is_active:
            border_col = (CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(240 * alpha))
            bw = max(1, int(1.8 * S))
        else:
            border_col = (255, 255, 255, ia(45 * alpha))
            bw = max(1, int(1.0 * S))

        draw.rounded_rectangle([x, y, x + w, y + h], radius=int(9.0 * S), fill=bg_col, outline=border_col, width=bw)

        # Text / Placeholder
        ty = y + (h - 24.0 * S) / 2.0
        tx = x + 16.0 * S

        if text:
            draw.text((tx, ty), text,
                      fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(255 * alpha)),
                      font=FONTS["r_13"])
        elif placeholder and not is_active:
            draw.text((tx, ty), placeholder,
                      fill=(CLR_TXT_MUTE[0], CLR_TXT_MUTE[1], CLR_TXT_MUTE[2], ia(110 * alpha)),
                      font=FONTS["r_13"])

        # Blinking Caret |
        if is_active and show_cursor:
            prefix = text[:cursor_pos]
            try:
                bb = FONTS["r_13"].getbbox(prefix)
                pw = bb[2] - bb[0]
            except Exception:
                pw = len(prefix) * int(8.0 * S)
            cx = tx + pw + 1.0 * S
            draw.line([(cx, y + 10.0 * S), (cx, y + h - 10.0 * S)],
                      fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(255 * alpha)),
                      width=max(1, int(2.0 * S)))

    def _draw_option_card(
        self,
        draw: ImageDraw.ImageDraw,
        x: float, y: float, w: float, h: float,
        title: str, subtitle: str,
        is_selected: bool,
        alpha: float, S: float,
    ):
        """Selectable card option with indicator and glowing focus border."""
        ia = lambda v: max(0, min(255, int(v)))

        if is_selected:
            bg_col = (20, 16, 32, ia(255 * alpha))
            border_col = (CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(220 * alpha))
            bw = max(1, int(1.8 * S))
        else:
            bg_col = (10, 10, 16, ia(255 * alpha))
            border_col = (255, 255, 255, ia(35 * alpha))
            bw = max(1, int(1.0 * S))

        draw.rounded_rectangle([x, y, x + w, y + h], radius=int(10.0 * S), fill=bg_col, outline=border_col, width=bw)

        # Radio / Indicator circle
        rcx = x + 24.0 * S
        rcy = y + h * 0.5
        rr = 8.0 * S
        draw.ellipse([rcx - rr, rcy - rr, rcx + rr, rcy + rr],
                     outline=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(220 * alpha if is_selected else 70 * alpha)),
                     width=max(1, int(1.6 * S)))
        if is_selected:
            dr = 4.5 * S
            draw.ellipse([rcx - dr, rcy - dr, rcx + dr, rcy + dr],
                         fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(255 * alpha)))

        # Title & Subtitle
        draw.text((x + 44.0 * S, y + 10.0 * S), title,
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(255 * alpha if is_selected else 215 * alpha)),
                  font=FONTS["d_13b"])
        draw.text((x + 44.0 * S, y + 32.0 * S), subtitle,
                  fill=(CLR_TXT_MUTE[0], CLR_TXT_MUTE[1], CLR_TXT_MUTE[2], ia(185 * alpha)),
                  font=FONTS["r_11"])

    def _draw_checkbox_card(
        self,
        draw: ImageDraw.ImageDraw,
        x: float, y: float, w: float, h: float,
        title: str, is_checked: bool,
        alpha: float, S: float,
    ):
        """Interactive obsidian checkbox row."""
        ia = lambda v: max(0, min(255, int(v)))

        bg_col = (18, 14, 28, ia(255 * alpha)) if is_checked else (10, 10, 16, ia(255 * alpha))
        border_col = (CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(200 * alpha)) if is_checked else (255, 255, 255, ia(40 * alpha))

        draw.rounded_rectangle([x, y, x + w, y + h], radius=int(10.0 * S), fill=bg_col, outline=border_col, width=max(1, int(1.4 * S)))

        # Checkbox square
        cb_x = x + 18.0 * S
        cb_y = y + (h - 20.0 * S) * 0.5
        cb_s = 20.0 * S
        draw.rounded_rectangle([cb_x, cb_y, cb_x + cb_s, cb_y + cb_s],
                               radius=int(4.0 * S),
                               fill=(26, 18, 40, ia(255 * alpha)) if is_checked else (14, 14, 22, ia(255 * alpha)),
                               outline=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(240 * alpha if is_checked else 80 * alpha)),
                               width=max(1, int(1.6 * S)))

        if is_checked:
            # Checkmark ✓
            chk_pts = [
                (cb_x + 4.0 * S, cb_y + 10.0 * S),
                (cb_x + 8.5 * S, cb_y + 15.0 * S),
                (cb_x + 16.0 * S, cb_y + 5.0 * S),
            ]
            draw.line(chk_pts, fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(255 * alpha)), width=max(1, int(2.4 * S)))

        # Text label
        draw.text((x + 50.0 * S, y + (h - 22.0 * S) * 0.5), title,
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(255 * alpha)),
                  font=FONTS["d_13b"])

    def _draw_voice_pill(
        self,
        draw: ImageDraw.ImageDraw,
        x: float, y: float, w: float, h: float,
        name: str, desc: str,
        is_selected: bool,
        alpha: float, S: float,
    ):
        """Voice option pill."""
        ia = lambda v: max(0, min(255, int(v)))

        if is_selected:
            bg = (32, 20, 52, ia(255 * alpha))
            border = (CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(230 * alpha))
            bw = max(1, int(1.8 * S))
        else:
            bg = (10, 10, 16, ia(255 * alpha))
            border = (255, 255, 255, ia(35 * alpha))
            bw = max(1, int(1.0 * S))

        draw.rounded_rectangle([x, y, x + w, y + h], radius=int(8.0 * S), fill=bg, outline=border, width=bw)
        draw.text((x + 12.0 * S, y + 6.0 * S), name,
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(255 * alpha if is_selected else 200 * alpha)),
                  font=FONTS["d_12b"])
        draw.text((x + 12.0 * S, y + 22.0 * S), desc,
                  fill=(CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(200 * alpha if is_selected else 140 * alpha)),
                  font=FONTS["m_9"])

    def _draw_style_pill(
        self,
        draw: ImageDraw.ImageDraw,
        x: float, y: float, w: float, h: float,
        label: str, is_selected: bool,
        alpha: float, S: float,
    ):
        """Conversational response style row pill."""
        ia = lambda v: max(0, min(255, int(v)))

        if is_selected:
            bg = (24, 18, 38, ia(255 * alpha))
            border = (CLR_LAVENDER[0], CLR_LAVENDER[1], CLR_LAVENDER[2], ia(220 * alpha))
            bw = max(1, int(1.6 * S))
        else:
            bg = (10, 10, 16, ia(255 * alpha))
            border = (255, 255, 255, ia(30 * alpha))
            bw = max(1, int(1.0 * S))

        draw.rounded_rectangle([x, y, x + w, y + h], radius=int(8.0 * S), fill=bg, outline=border, width=bw)
        draw.text((x + 16.0 * S, y + (h - 22.0 * S) * 0.5), label,
                  fill=(CLR_TXT_MAIN[0], CLR_TXT_MAIN[1], CLR_TXT_MAIN[2], ia(255 * alpha if is_selected else 190 * alpha)),
                  font=FONTS["r_12"])

    def to_premultiplied_bgra(self, img: Image.Image) -> bytes:
        """
        Fast vectorized conversion from Pillow RGBA → 32-bit Premultiplied BGRA.
        """
        arr = np.frombuffer(img.tobytes(), dtype=np.uint8).reshape((img.height, img.width, 4))
        if arr.size == 0:
            return b""
        a = arr[:, :, 3].astype(np.uint16)
        bgra = np.empty_like(arr)
        bgra[:, :, 0] = (arr[:, :, 2].astype(np.uint16) * a // 255).astype(np.uint8)  # B
        bgra[:, :, 1] = (arr[:, :, 1].astype(np.uint16) * a // 255).astype(np.uint8)  # G
        bgra[:, :, 2] = (arr[:, :, 0].astype(np.uint16) * a // 255).astype(np.uint8)  # R
        bgra[:, :, 3] = arr[:, :, 3]                                                 # A
        return bgra.tobytes()

