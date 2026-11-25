# -*- coding: utf-8 -*-
"""
Equalizer APO 预设实时切换器（RVC STUDIO 风格 UI）
- 自动发现 F:\\int\\eq 下的 *.txt 预设
- 点击即切换（写 config.txt，APO 自动重载）
- 需要管理员权限（写 Program Files）
仅使用标准库：tkinter / ctypes / os / shutil / sys / time
"""
import ctypes
import math
import os
import re
import shutil
import json
import sys
import time
import threading
import queue
import tkinter as tk
import webbrowser
import winreg
from tkinter import filedialog, messagebox, simpledialog

def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _has_presets(path):
    try:
        return os.path.isdir(path) and any(
            f.lower().endswith(".txt") for f in os.listdir(path))
    except OSError:
        return False


EQ_DIR = r"F:\int\eq"
if not _has_presets(EQ_DIR):
    EQ_DIR = os.path.join(base_dir(), "presets")

def _bundled_dir(name):
    base = getattr(sys, "_MEIPASS", base_dir())
    path = os.path.join(base, name)
    return path if os.path.isdir(path) else None


def ensure_local_presets():
    """回退到本地 presets 时，把随程序打包的预设复制过去。"""
    local = os.path.join(base_dir(), "presets")
    if os.path.abspath(EQ_DIR) != os.path.abspath(local):
        return
    os.makedirs(local, exist_ok=True)
    src = _bundled_dir("presets")
    if not src:
        return
    for name in os.listdir(src):
        if name.lower().endswith(".txt"):
            dst = os.path.join(local, name)
            if not os.path.exists(dst):
                try:
                    shutil.copyfile(os.path.join(src, name), dst)
                except OSError:
                    pass


APO_STATE = os.path.join(base_dir(), "apo_path.json")


def load_saved_apo():
    try:
        with open(APO_STATE, "r", encoding="utf-8") as fh:
            return json.load(fh).get("config_dir")
    except Exception:
        return None


def save_apo_dir(path):
    try:
        with open(APO_STATE, "w", encoding="utf-8") as fh:
            json.dump({"config_dir": path}, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def find_apo_dir():
    cands = []
    saved = load_saved_apo()
    if saved:
        cands.append(saved)
    env = os.environ.get("EQUALIZERAPO_CONFIG")
    if env:
        cands.append(env)
    for sub in (r"SOFTWARE\EqualizerAPO", r"SOFTWARE\WOW6432Node\EqualizerAPO"):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub) as k:
                try:
                    cands.append(winreg.QueryValueEx(k, "ConfigPath")[0])
                except OSError:
                    pass
                try:
                    cands.append(os.path.join(
                        winreg.QueryValueEx(k, "InstallPath")[0], "config"))
                except OSError:
                    pass
        except OSError:
            pass
    for pf in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if pf:
            cands.append(os.path.join(pf, "EqualizerAPO", "config"))
    for letter in "CDEFGH":
        cands.append(os.path.join(letter + ":\\Program Files\\EqualizerAPO\\config"))
        cands.append(os.path.join(letter + ":\\Program Files (x86)\\EqualizerAPO\\config"))
    for c in cands:
        if c and os.path.isdir(c) and os.path.exists(os.path.join(c, "config.txt")):
            return c
    for c in cands:
        if c and os.path.isdir(c):
            return c
    return None


ensure_local_presets()
APO_DIR = find_apo_dir() or r"C:\Program Files\EqualizerAPO\config"
CFG = os.path.join(APO_DIR, "config.txt")

NAME_MAP = {
    "hd490pro-oratory-mix.txt": "490 Pro 实测校准（绒布耳罩）",
    "hd490pro-oratory-prod.txt": "490 Pro 实测校准（厚布耳罩）",
    "hd490pro.txt": "490 Pro 我调 · 补低频+人声",
    "hd490pro-night.txt": "490 Pro 夜间/低音量",
    "hd490pro-thick.txt": "490 Pro 厚声模拟（老功放味）",
    "hd490pro-game.txt": "490 Pro 打瓦 HRTF（通用）",
    "hd490pro-valorant.txt": "490 Pro 打瓦专用（脚步强化）",
    "hd490pro-valorant-hrtf.txt": "490 Pro 打瓦·HRTF 补偿版",
    "hd490pro-sim-dt700.txt": "490 Pro 模拟 DT 700（厚低频）",
    "hd490pro-sim-hd800s.txt": "490 Pro 模拟 HD 800S（6k峰）",
    "dt700.txt": "DT 700 Pro X 听歌",
    "h6air-harman.txt": "H6 Air · Harman 目标（参数）",
    "h6air-graphic.txt": "H6 Air · Harman 目标（图形）",
}

GROUP_ORDER = ["HD 490 PRO", "DT 700 Pro X", "Sony INZONE H6 Air", "其他"]


def preset_group(fn):
    low = fn.lower()
    if low.startswith("hd490pro"):
        return "HD 490 PRO"
    if low.startswith("dt700"):
        return "DT 700 Pro X"
    if low.startswith("h6air"):
        return "Sony INZONE H6 Air"
    return "其他"

# ---- RVC STUDIO 风格配色 ----
LIGHT = {
    "BG": "#eef1f6", "CARD": "#ffffff", "BORDER": "#e3e8f0",
    "TEXT": "#16233d", "MUTED": "#7b8496", "ACCENT": "#2f5bea",
    "ACCENT_DARK": "#2448c9", "ACCENT_SOFT": "#eaf0ff",
    "GREEN": "#1f9d55", "RED": "#d64545", "HOVER": "#f6f8fc",
    "ORANGE": "#b45309", "ORANGE_SOFT": "#fff7ed",
    "GRID": "#eef1f6", "AXIS": "#d9dee8",
    "DANGER_BG": "#fff5f5", "DANGER_HOVER": "#ffecec",
    "DANGER_BORDER": "#f3c7c7", "WHITE": "#ffffff",
}
DARK = {
    "BG": "#10151d", "CARD": "#1a2230", "BORDER": "#2a3445",
    "TEXT": "#e7edf7", "MUTED": "#8c9ab0", "ACCENT": "#5b8cff",
    "ACCENT_DARK": "#7aa2ff", "ACCENT_SOFT": "#1d2c4a",
    "GREEN": "#2fbf71", "RED": "#ff6b6b", "HOVER": "#222d3f",
    "ORANGE": "#f0a35e", "ORANGE_SOFT": "#3a2a1c",
    "GRID": "#2f3d52", "AXIS": "#465a78",
    "DANGER_BG": "#3a1f22", "DANGER_HOVER": "#4a2428",
    "DANGER_BORDER": "#6b3a3f", "WHITE": "#ffffff",
}
PALETTE = LIGHT
BG = LIGHT["BG"]
CARD = LIGHT["CARD"]
BORDER = LIGHT["BORDER"]
TEXT = LIGHT["TEXT"]
MUTED = LIGHT["MUTED"]
ACCENT = LIGHT["ACCENT"]
ACCENT_DARK = LIGHT["ACCENT_DARK"]
ACCENT_SOFT = LIGHT["ACCENT_SOFT"]
GREEN = LIGHT["GREEN"]
RED = LIGHT["RED"]
HOVER = LIGHT["HOVER"]
ORANGE = LIGHT["ORANGE"]
ORANGE_SOFT = LIGHT["ORANGE_SOFT"]
GRID = LIGHT["GRID"]
AXIS = LIGHT["AXIS"]
DANGER_BG = LIGHT["DANGER_BG"]
DANGER_HOVER = LIGHT["DANGER_HOVER"]
DANGER_BORDER = LIGHT["DANGER_BORDER"]
FONT = "Microsoft YaHei UI"


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def lerp_hex(a, b, t):
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)
    return rgb_to_hex(tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3)))


def nearest_color_key(value):
    try:
        rgb = hex_to_rgb(str(value))
    except Exception:
        return None
    best, best_d = None, 1e9
    for key in LIGHT:
        for pal in (LIGHT, DARK):
            try:
                prgb = hex_to_rgb(pal[key])
            except Exception:
                continue
            d = ((rgb[0] - prgb[0]) ** 2 + (rgb[1] - prgb[1]) ** 2
                 + (rgb[2] - prgb[2]) ** 2)
            if d < best_d:
                best, best_d = key, d
    if best_d <= 110 * 110:
        return best
    return None


def resolve_color_key(value, option):
    text = str(value).upper()
    if text == "#FFFFFF":
        return "CARD" if "background" in option else "WHITE"
    return COLOR_KEY.get(text)


COLOR_KEY = {}
for _k, _v in LIGHT.items():
    COLOR_KEY[_v.upper()] = _k
for _k, _v in DARK.items():
    COLOR_KEY.setdefault(_v.upper(), _k)


def set_palette_values(pal):
    global PALETTE, BG, CARD, BORDER, TEXT, MUTED, ACCENT, ACCENT_DARK
    global ACCENT_SOFT, GREEN, RED, HOVER, ORANGE, ORANGE_SOFT
    global GRID, AXIS, DANGER_BG, DANGER_HOVER, DANGER_BORDER
    PALETTE = pal
    BG = pal["BG"]
    CARD = pal["CARD"]
    BORDER = pal["BORDER"]
    TEXT = pal["TEXT"]
    MUTED = pal["MUTED"]
    ACCENT = pal["ACCENT"]
    ACCENT_DARK = pal["ACCENT_DARK"]
    ACCENT_SOFT = pal["ACCENT_SOFT"]
    GREEN = pal["GREEN"]
    RED = pal["RED"]
    HOVER = pal["HOVER"]
    ORANGE = pal["ORANGE"]
    ORANGE_SOFT = pal["ORANGE_SOFT"]
    GRID = pal["GRID"]
    AXIS = pal["AXIS"]
    DANGER_BG = pal["DANGER_BG"]
    DANGER_HOVER = pal["DANGER_HOVER"]
    DANGER_BORDER = pal["DANGER_BORDER"]


def set_dark_titlebar(root, dark):
    try:
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetAncestor(root.winfo_id(), 2)
        value = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attr, ctypes.byref(value), ctypes.sizeof(value))
        ctypes.windll.user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0004 | 0x0020)
    except Exception:
        pass


def apply_palette(dark):
    global PALETTE, BG, CARD, BORDER, TEXT, MUTED, ACCENT, ACCENT_DARK
    global ACCENT_SOFT, GREEN, RED, HOVER, ORANGE, ORANGE_SOFT
    global GRID, AXIS, DANGER_BG, DANGER_HOVER, DANGER_BORDER
    PALETTE = DARK if dark else LIGHT
    BG = PALETTE["BG"]
    CARD = PALETTE["CARD"]
    BORDER = PALETTE["BORDER"]
    TEXT = PALETTE["TEXT"]
    MUTED = PALETTE["MUTED"]
    ACCENT = PALETTE["ACCENT"]
    ACCENT_DARK = PALETTE["ACCENT_DARK"]
    ACCENT_SOFT = PALETTE["ACCENT_SOFT"]
    GREEN = PALETTE["GREEN"]
    RED = PALETTE["RED"]
    HOVER = PALETTE["HOVER"]
    ORANGE = PALETTE["ORANGE"]
    ORANGE_SOFT = PALETTE["ORANGE_SOFT"]
    GRID = PALETTE["GRID"]
    AXIS = PALETTE["AXIS"]
    DANGER_BG = PALETTE["DANGER_BG"]
    DANGER_HOVER = PALETTE["DANGER_HOVER"]
    DANGER_BORDER = PALETTE["DANGER_BORDER"]


def rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kw)


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, kind="ghost", width=110, height=34):
        bg = parent.cget("bg") if isinstance(parent, tk.Frame) else BG
        super().__init__(parent, width=width, height=height, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.text = text
        self.command = command
        self.kind = kind
        self.bw, self.bh = width, height
        self._hover = False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", lambda e: self.command())
        self._draw()

    def _palette(self):
        if self.kind == "primary":
            fill = ACCENT if not self._hover else ACCENT_DARK
            text = "#ffffff"
            outline = fill
        elif self.kind == "danger":
            fill = DANGER_BG if not self._hover else DANGER_HOVER
            text = RED
            outline = DANGER_BORDER
        else:
            fill = CARD if not self._hover else HOVER
            text = TEXT
            outline = BORDER
        return fill, text, outline

    def _draw(self):
        self.delete("all")
        fill, text, outline = self._palette()
        rounded_rect(self, 1, 1, self.bw - 1, self.bh - 1, 9,
                     fill=fill, outline=outline)
        self.create_text(self.bw / 2, self.bh / 2, text=self.text,
                         fill=text, font=(FONT, 9))

    def _on_enter(self, _e):
        self._hover = True
        self._draw()

    def _on_leave(self, _e):
        self._hover = False
        self._draw()


class DeviceSelector(tk.Canvas):
    """圆角设备选择器：点击弹出 Toplevel 列表，选中即回调。"""

    def __init__(self, parent, options, width=262, height=32):
        super().__init__(parent, width=width, height=height, bg=BG,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bw, self.bh = width, height
        self.options = list(options)
        self.value = self.options[0]
        self.on_change = None
        self._pop = None
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._open)
        self._draw()

    def get(self):
        return self.value

    def set(self, value):
        if value in self.options:
            self.value = value
            self._draw()

    def set_options(self, options, keep=None):
        self.options = list(options)
        if keep and keep in self.options:
            self.value = keep
        elif self.value not in self.options:
            self.value = self.options[0]
        self._draw()

    def _draw(self):
        self.delete("all")
        rounded_rect(self, 1, 1, self.bw - 1, self.bh - 1, 9,
                     fill=CARD, outline=BORDER)
        text = self.value
        if len(text) > 26:
            text = text[:25] + "…"
        self.create_text(12, self.bh / 2, text=text, anchor="w",
                         fill=TEXT, font=(FONT, 9))
        self.create_text(self.bw - 14, self.bh / 2, text="▾", anchor="e",
                         fill=MUTED, font=(FONT, 9))

    def _open(self, _e=None):
        self._close_popup()
        top = tk.Toplevel(self)
        top.overrideredirect(True)
        top.configure(bg=BORDER)
        frame = tk.Frame(top, bg=CARD)
        frame.pack(padx=1, pady=1, fill="both", expand=True)
        for opt in self.options:
            lbl = tk.Label(frame, text=opt, anchor="w", bg=CARD, fg=TEXT,
                           font=(FONT, 9), padx=14, pady=6, cursor="hand2")
            lbl.pack(fill="x")
            lbl.bind("<Enter>", lambda e, l=lbl: l.configure(bg=ACCENT_SOFT))
            lbl.bind("<Leave>", lambda e, l=lbl: l.configure(bg=CARD))
            lbl.bind("<Button-1>", lambda e, o=opt: self._choose(o))
        top.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.bh + 2
        top.attributes("-topmost", True)
        top.geometry("+%d+%d" % (x, y))
        top.update()
        top.lift()
        top.focus_force()
        top.bind("<FocusOut>", lambda e: self._close_popup())
        top.bind("<Escape>", lambda e: self._close_popup())
        self._pop = top

    def _choose(self, value):
        self.value = value
        self._draw()
        self._close_popup()
        if self.on_change:
            self.on_change()

    def _close_popup(self):
        if self._pop is not None:
            try:
                self._pop.destroy()
            except tk.TclError:
                pass
            self._pop = None


class ToggleChip(tk.Canvas):
    """小型开关胶囊：用于「含未连接」等布尔选项。"""

    def __init__(self, parent, text, value=False, command=None,
                 width=86, height=32):
        super().__init__(parent, width=width, height=height, bg=BG,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bw, self.bh = width, height
        self.text = text
        self.value = value
        self.command = command
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._toggle)
        self._draw()

    def get(self):
        return self.value

    def _fit(self):
        self._draw()

    def _toggle(self, _e=None):
        self.value = not self.value
        self._draw()
        if self.command:
            self.command()

    def _draw(self):
        self.delete("all")
        fill = ACCENT_SOFT if self.value else CARD
        outline = ACCENT if self.value else BORDER
        rounded_rect(self, 1, 1, self.bw - 1, self.bh - 1, 9,
                     fill=fill, outline=outline)
        self.create_text(self.bw / 2, self.bh / 2, text=self.text,
                         fill=ACCENT if self.value else MUTED,
                         font=(FONT, 8))


class PinButton(tk.Canvas):
    """置顶开关：钉子图标 + 文字，激活时蓝色高亮。"""

    def __init__(self, parent, value=True, command=None, width=76, height=28):
        super().__init__(parent, width=width, height=height, bg=BG,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bw, self.bh = width, height
        self.value = bool(value)
        self.command = command
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._toggle)
        self._draw()

    def get(self):
        return self.value

    def set(self, value):
        self.value = bool(value)
        self._draw()

    def _toggle(self, _e=None):
        self.value = not self.value
        self._draw()
        if self.command:
            self.command()

    def _draw(self):
        self.delete("all")
        fill = ACCENT_SOFT if self.value else CARD
        outline = ACCENT if self.value else BORDER
        fg = ACCENT if self.value else MUTED
        rounded_rect(self, 1, 1, self.bw - 1, self.bh - 1, 9,
                     fill=fill, outline=outline)
        # 简易钉子图标
        cx, cy = 15, self.bh / 2
        self.create_oval(cx - 4, cy - 6, cx + 4, cy + 2,
                         fill=fg, outline=fg)
        self.create_line(cx, cy + 1, cx, cy + 8, fill=fg, width=2)
        self.create_text(cx + 12, cy, text="置顶", anchor="w",
                         fill=fg, font=(FONT, 8))


class Card(tk.Frame):
    """白底圆角卡片：用 Canvas 画背景，内部放 Frame。"""

    def __init__(self, parent, radius=14):
        super().__init__(parent, bg=BG)
        self.radius = radius
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=CARD)
        self._win = self.canvas.create_window(14, 12, anchor="nw", window=self.body)
        self.canvas.bind("<Configure>", self._redraw)

    def _redraw(self, _e=None):
        self.canvas.delete("bg")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        rounded_rect(self.canvas, 1, 1, w - 1, h - 1, self.radius,
                     fill=CARD, outline=BORDER, tags="bg")
        self.canvas.tag_lower("bg")
        self.canvas.itemconfigure(self._win, width=w - 28, height=max(1, h - 24))


class ThemeSwitch(tk.Canvas):
    """太阳 / 月亮分段开关（无滑钮）。"""

    def __init__(self, parent, value=False, command=None, width=84, height=30):
        super().__init__(parent, width=width, height=height, bg=BG,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bw, self.bh = width, height
        self.value = bool(value)
        self.command = command
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._click)
        self._draw()

    def get(self):
        return self.value

    def set(self, value):
        self.value = bool(value)
        self._draw()

    def _click(self, event):
        target = event.x >= self.bw / 2
        if target != self.value:
            self.value = target
            self._draw()
            if self.command:
                self.command()

    def _draw(self):
        self.delete("all")
        w, h = self.bw, self.bh
        cy = h / 2
        r = (h - 2) / 2
        rounded_rect(self, 1, 1, w - 1, h - 1, r, fill=CARD, outline=BORDER)
        if self.value:
            rounded_rect(self, w / 2 - 8, 2, w - 2, h - 2, r - 1,
                         fill=ACCENT_SOFT, outline=ACCENT_SOFT)
        else:
            rounded_rect(self, 2, 2, w / 2 + 8, h - 2, r - 1,
                         fill=ACCENT_SOFT, outline=ACCENT_SOFT)
        self.create_line(w / 2, 5, w / 2, h - 5, fill=BORDER)
        sun_col = MUTED if self.value else ACCENT
        moon_col = ACCENT if self.value else MUTED
        moon_bg = ACCENT if self.value else CARD
        # 太阳
        sx, sy = w * 0.25, cy
        self.create_oval(sx - 3, sy - 3, sx + 3, sy + 3,
                         outline=sun_col, width=1.4)
        for dx, dy in ((0, -7.5), (0, 7.5), (-7.5, 0), (7.5, 0),
                       (-5.5, -5.5), (5.5, -5.5), (-5.5, 5.5), (5.5, 5.5)):
            self.create_line(sx + dx * 0.62, sy + dy * 0.62,
                             sx + dx, sy + dy, fill=sun_col, width=1)
        # 月亮
        mx, my = w * 0.75, cy
        self.create_oval(mx - 4.5, my - 5, mx + 4.5, my + 5,
                         outline=moon_col, width=1.4)
        self.create_oval(mx - 0.5, my - 6, mx + 7.5, my + 4.5,
                         outline=moon_bg, fill=moon_bg, width=0)


class GroupHeader(tk.Canvas):
    """设备分组标题：点击展开/收起。"""

    def __init__(self, parent, title, count, expanded, command):
        super().__init__(parent, bg=CARD, highlightthickness=0, bd=0,
                         height=34, cursor="hand2")
        self.title = title
        self.count = count
        self.expanded = expanded
        self.command = command
        self._hover = False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", lambda e: self.command())

    def _enter(self, _e):
        self._hover = True
        self._draw()

    def _leave(self, _e):
        self._hover = False
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or 360
        h = self.winfo_height() or 34
        fill = HOVER if self._hover else CARD
        rounded_rect(self, 1, 2, w - 1, h - 2, 8, fill=fill, outline=fill)
        arrow = "▾" if self.expanded else "▸"
        self.create_text(12, h / 2, text=arrow, anchor="w",
                         fill=MUTED, font=(FONT, 8))
        self.create_text(26, h / 2, text=self.title, anchor="w",
                         fill=TEXT, font=(FONT, 9, "bold"))
        self.create_text(w - 12, h / 2, text="%d" % self.count, anchor="e",
                         fill=MUTED, font=(FONT, 8))


class PresetRow(tk.Canvas):
    """圆角预设行：悬停高亮、当前项浅蓝底 + 左侧圆角竖条。"""

    def __init__(self, parent, label, active, command, fn="", on_context=None):
        super().__init__(parent, bg=CARD, highlightthickness=0, bd=0,
                         height=40, cursor="hand2")
        self.label = label
        self.active = active
        self.command = command
        self.fn = fn
        self.on_context = on_context
        self._hover = False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", lambda e: self.command())
        if on_context:
            self.bind("<Button-3>", self._context)

    def _context(self, event):
        if self.on_context:
            self.on_context(self.fn, event)

    def _enter(self, _e):
        if not self.active:
            self._hover = True
            self._draw()

    def _leave(self, _e):
        if self._hover:
            self._hover = False
            self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or 400
        h = self.winfo_height() or 46
        fill = ACCENT_SOFT if self.active else (HOVER if self._hover else CARD)
        rounded_rect(self, 1, 2, w - 1, h - 2, 9,
                     fill=fill, outline=fill)
        tx = 18
        if self.active:
            rounded_rect(self, 7, 11, 11, h - 11, 2,
                         fill=ACCENT, outline=ACCENT)
            tx = 24
            self.create_text(tx, h / 2, text=self.label, anchor="w",
                             fill=ACCENT, font=(FONT, 10, "bold"))
            self.create_text(w - 12, h / 2, text="● 已启用", anchor="e",
                             fill=ACCENT, font=(FONT, 8))
        else:
            self.create_text(tx, h / 2, text=self.label, anchor="w",
                             fill=TEXT, font=(FONT, 10))


STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_state.json")


def _recycle(path):
    """用 SHFileOperation 把文件移到回收站。"""
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", ctypes.c_uint16),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", wintypes.LPVOID),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    FO_DELETE = 3
    FOF_ALLOWUNDO = 0x0040
    FOF_NOCONFIRMATION = 0x0010
    FOF_SILENT = 0x0004
    op = SHFILEOPSTRUCTW()
    op.hwnd = None
    op.wFunc = FO_DELETE
    op.pFrom = path + "\0"
    op.pTo = None
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
    res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if res != 0:
        raise OSError("SHFileOperation 返回 %d" % res)


def resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, name)
    return path if os.path.exists(path) else None


OPRA_URL = "http://opra.roonlabs.net/database_v1.jsonl"
OPRA_CACHE = os.path.join(base_dir(), "opra_database_v1.jsonl")


def load_opra_database(path=None):
    path = path or OPRA_CACHE
    vendors, products, eqs = {}, {}, {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            kind = obj.get("type")
            data = obj.get("data") or {}
            if kind == "vendor":
                vendors[obj.get("id")] = data
            elif kind == "product":
                products[obj.get("id")] = data
            elif kind == "eq":
                pid = data.get("product_id")
                eqs.setdefault(pid, []).append(data)
    return vendors, products, eqs


OPRA_URLS = (
    "https://opra.roonlabs.net/database_v1.jsonl",
    "http://opra.roonlabs.net/database_v1.jsonl",
    "https://raw.githubusercontent.com/opra-project/OPRA/main/dist/database_v1.jsonl",
)


def download_opra_database(progress=None):
    import urllib.request
    import urllib.error
    tmp = OPRA_CACHE + ".part"
    headers = {
        "User-Agent": "EQSwitcher/2.1 (+https://github.com/Mavic-png/eq-switcher)",
        "Accept": "application/jsonl,application/octet-stream,*/*",
    }
    last_error = None
    for url in OPRA_URLS:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as src:
                try:
                    total = int(src.headers.get("Content-Length") or 0)
                except Exception:
                    total = 0
                done = 0
                with open(tmp, "wb") as dst:
                    while True:
                        chunk = src.read(256 * 1024)
                        if not chunk:
                            break
                        dst.write(chunk)
                        done += len(chunk)
                        if progress:
                            try:
                                progress(done, total)
                            except Exception:
                                pass
            if os.path.getsize(tmp) < 1024 * 1024:
                raise RuntimeError("下载内容不完整")
            os.replace(tmp, OPRA_CACHE)
            return
        except urllib.error.HTTPError as exc:
            last_error = "%s: HTTP %s" % (url, exc.code)
        except Exception as exc:  # noqa: BLE001
            last_error = "%s: %s" % (url, exc)
    try:
        if os.path.exists(tmp):
            os.remove(tmp)
    except OSError:
        pass
    raise RuntimeError(last_error or "下载失败")


def opra_filter_line(index, band):
    kind = {"low_shelf": "LS", "high_shelf": "HS",
            "peak_dip": "PK", "peak": "PK"}.get(band.get("type"), "PK")
    return ("Filter %d: ON %s Fc %g Hz Gain %g dB Q %g"
            % (index, kind, float(band.get("frequency", 1000)),
               float(band.get("gain_db", 0)), float(band.get("q", 1.0))))


def opra_to_preset(eq):
    params = eq.get("parameters") or {}
    lines = ["Preamp: %g dB" % float(params.get("gain_db", 0))]
    for i, band in enumerate(params.get("bands") or [], 1):
        lines.append(opra_filter_line(i, band))
    return "\n".join(lines) + "\n"


def safe_preset_name(text, fallback="opra-preset"):
    name = re.sub(r'[\\/:*?"<>|]', "_", text)
    name = re.sub(r'\s+', "_", name).strip().strip("._")
    return name or fallback


def load_ui_state():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_ui_state(data):
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def parse_preset(path):
    """解析 Equalizer APO 预设，返回 (preamp, filters)。"""
    preamp = 0.0
    filters = []
    graphic = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                s = line.strip()
                low = s.lower()
                if low.startswith("preamp:"):
                    m = re.search(r"preamp:\s*(-?[\d.]+)", s, re.I)
                    if m:
                        preamp += float(m.group(1))
                elif low.startswith("include:"):
                    name = s.split(":", 1)[1].strip()
                    sub = os.path.join(EQ_DIR, name)
                    if os.path.isfile(sub):
                        p2, f2 = parse_preset(sub)
                        preamp += p2
                        filters.extend(f2)
                elif low.startswith("filter"):
                    m = re.match(r"filter\s*\d*\s*:\s*(on|off)\s+(\w+)\s*(.*)", s, re.I)
                    if not m or m.group(1).lower() == "off":
                        continue
                    typ = m.group(2).upper()
                    params = m.group(3)
                    fc = re.search(r"fc\s+([\d.]+)\s*hz", params, re.I)
                    if not fc:
                        continue
                    gain = re.search(r"gain\s+(-?[\d.]+)\s*db", params, re.I)
                    q = re.search(r"q\s+([\d.]+)", params, re.I)
                    filters.append({
                        "type": typ,
                        "f": float(fc.group(1)),
                        "g": float(gain.group(1)) if gain else 0.0,
                        "q": float(q.group(1)) if q else None,
                    })
                elif low.startswith("graphiceq:"):
                    body = s.split(":", 1)[1]
                    for pair in body.split(";"):
                        parts = pair.split()
                        if len(parts) >= 2:
                            try:
                                graphic.append((float(parts[0]), float(parts[1])))
                            except ValueError:
                                pass
    except Exception:
        pass
    return preamp, filters, graphic


def _biquad_mag(ftype, f0, gain, q, fs=48000.0):
    """返回 (b0,b1,b2,a0,a1,a2) 或 None。"""
    w0 = 2 * math.pi * f0 / fs
    cw = math.cos(w0)
    sw = math.sin(w0)
    A = 10 ** (gain / 40.0)
    if not q or q <= 0:
        q = 0.7071
    alpha = sw / (2 * q)
    if ftype in ("PK", "PEQ", "MODAL"):
        b0, b1, b2 = 1 + alpha * A, -2 * cw, 1 - alpha * A
        a0, a1, a2 = 1 + alpha / A, -2 * cw, 1 - alpha / A
    elif ftype in ("LS", "LSC"):
        S = 1.0
        beta = sw * math.sqrt(max(0.0, (A * A + 1) / S - (A - 1) ** 2))
        b0 = A * ((A + 1) - (A - 1) * cw + beta)
        b1 = 2 * A * ((A - 1) - (A + 1) * cw)
        b2 = A * ((A + 1) - (A - 1) * cw - beta)
        a0 = (A + 1) + (A - 1) * cw + beta
        a1 = -2 * ((A - 1) + (A + 1) * cw)
        a2 = (A + 1) + (A - 1) * cw - beta
    elif ftype in ("HS", "HSC"):
        S = 1.0
        beta = sw * math.sqrt(max(0.0, (A * A + 1) / S - (A - 1) ** 2))
        b0 = A * ((A + 1) + (A - 1) * cw + beta)
        b1 = -2 * A * ((A - 1) + (A + 1) * cw)
        b2 = A * ((A + 1) + (A - 1) * cw - beta)
        a0 = (A + 1) - (A - 1) * cw + beta
        a1 = 2 * ((A - 1) - (A + 1) * cw)
        a2 = (A + 1) - (A - 1) * cw - beta
    elif ftype in ("LP", "LPQ"):
        b0, b1, b2 = (1 - cw) / 2, 1 - cw, (1 - cw) / 2
        a0, a1, a2 = 1 + alpha, -2 * cw, 1 - alpha
    elif ftype in ("HP", "HPQ"):
        b0, b1, b2 = (1 + cw) / 2, -(1 + cw), (1 + cw) / 2
        a0, a1, a2 = 1 + alpha, -2 * cw, 1 - alpha
    elif ftype == "NO":
        b0, b1, b2 = 1.0, -2 * cw, 1.0
        a0, a1, a2 = 1 + alpha, -2 * cw, 1 - alpha
    elif ftype == "BP":
        b0, b1, b2 = alpha, 0.0, -alpha
        a0, a1, a2 = 1 + alpha, -2 * cw, 1 - alpha
    else:
        return None
    return (b0, b1, b2, a0, a1, a2)


def estimate_compensation(preamp, filters, graphic=None, target=0.0):
    """按 100Hz–8kHz 平均响应估算补偿，并保证不因提升而削波。"""
    try:
        freqs, gains = response_curve(preamp, filters, graphic)
        vals = [g for f, g in zip(freqs, gains) if 100.0 <= f <= 8000.0]
        if not vals:
            return 0.0
        avg = sum(vals) / len(vals)
        peak = max(gains)
        comp = target - avg
        comp = min(comp, -peak)  # 保证峰值不超过 0 dBFS
        return max(-12.0, min(12.0, comp))
    except Exception:
        return 0.0


def response_curve(preamp, filters, graphic=None, fs=48000.0, n=360):
    freqs = [20 * (1000 ** (i / (n - 1))) for i in range(n)]
    graphic = sorted(graphic or [])
    coefs = []
    for flt in filters:
        co = _biquad_mag(flt["type"], flt["f"], flt["g"], flt["q"], fs)
        if co:
            coefs.append(co)
    dbs = []
    for f in freqs:
        total = 10 ** (preamp / 20.0)
        for (b0, b1, b2, a0, a1, a2) in coefs:
            w = 2 * math.pi * f / fs
            z = complex(math.cos(-w), math.sin(-w))
            num = b0 + b1 * z + b2 * z * z
            den = a0 + a1 * z + a2 * z * z
            if abs(den) > 1e-12:
                total *= abs(num) / abs(den)
        db = 20 * math.log10(max(total, 1e-9))
        if graphic:
            gf, gd = zip(*graphic)
            if f <= gf[0]:
                db += gd[0]
            elif f >= gf[-1]:
                db += gd[-1]
            else:
                for i in range(len(gf) - 1):
                    if gf[i] <= f <= gf[i + 1]:
                        t0 = math.log(f / gf[i]) / math.log(gf[i + 1] / gf[i])
                        db += gd[i] * (1 - t0) + gd[i + 1] * t0
                        break
        dbs.append(db)
    return freqs, dbs


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin():
    params = " ".join('"%s"' % a for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, os.getcwd(), 1)


def discover():
    out = []
    if not os.path.isdir(EQ_DIR):
        return out
    for fn in sorted(os.listdir(EQ_DIR)):
        if fn.lower().endswith(".txt"):
            out.append(fn)
    order = {k: i for i, k in enumerate(NAME_MAP.keys())}
    out.sort(key=lambda f: (order.get(f, 99), f))
    return out


def list_output_devices():
    """枚举 Windows 播放设备（注册表 MMDevices\\Audio\\Render）。"""
    base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render"
    out = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as root:
            i = 0
            while True:
                try:
                    guid = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                try:
                    k = winreg.OpenKey(root, guid)
                except OSError:
                    continue
                state = None
                friendly = ""
                desc = ""
                try:
                    state = winreg.QueryValueEx(k, "DeviceState")[0]
                except OSError:
                    pass
                try:
                    with winreg.OpenKey(k, "Properties") as pk:
                        friendly = winreg.QueryValueEx(
                            pk, "{b3f8fa53-0004-438e-9003-51a46e139bfc},6")[0]
                        desc = winreg.QueryValueEx(
                            pk, "{a45c254e-df1c-4efd-8020-67d146a850e0},2")[0]
                except OSError:
                    pass
                active = bool(state is not None and (state & 1))
                label = friendly or desc or guid
                if friendly and desc and desc not in label:
                    label = "%s · %s" % (friendly, desc)
                if not active:
                    label += "（未连接）"
                pattern = ("%s %s; %s" % (friendly, desc, guid)).strip()
                out.append((active, label, pattern, guid))
    except OSError:
        return []
    out.sort(key=lambda x: (not x[0], x[1]))
    return out


def read_config_state():
    device = None
    include = None
    try:
        with open(CFG, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                s = line.strip()
                low = s.lower()
                if low.startswith("device:"):
                    device = s.split(":", 1)[1].strip()
                elif low.startswith("include:"):
                    include = s.split(":", 1)[1].strip()
    except Exception:
        pass
    return device, include


class PeqEditor(tk.Toplevel):
    """内置参数均衡编辑器：拖动频点改频率/增益，滚轮改 Q，实时曲线。"""

    LEFT, RIGHT, TOP, BOTTOM = 46, 14, 16, 34
    DB_RANGE = 12.0

    def __init__(self, master, on_saved=None, app=None, initial=None,
                 target_fn=None):
        super().__init__(master)
        self.on_saved = on_saved
        self.app = app
        self.target_fn = target_fn
        self.previewing = False
        self.restore_fn = None
        self._preview_job = None
        self.filters = []
        self.graphic = []
        self.selected = -1
        self.preamp = 0.0
        self.drag = None
        self._cursor = None
        if initial:
            self.preamp = float(initial.get("preamp") or 0.0)
            self.filters = [dict(f) for f in (initial.get("filters") or [])]
            self.graphic = [tuple(g) for g in (initial.get("graphic") or [])]
        if target_fn:
            self.title("编辑预设 - %s" % NAME_MAP.get(target_fn,
                                                    target_fn))
        else:
            self.title("PEQ 编辑器")
        self.configure(bg=BG)
        self.transient(master)
        self.attributes("-topmost", True)
        self.geometry("680x520+%d+%d" % (master.winfo_rootx() + 120,
                                         master.winfo_rooty() + 90))

        ctrl = tk.Frame(self, bg=BG)
        ctrl.pack(fill="x", padx=14, pady=(12, 6))
        self.preamp_var = tk.StringVar(value="0.0")
        self.fc_var = tk.StringVar(value="1000")
        self.gain_var = tk.StringVar(value="0.0")
        self.q_var = tk.StringVar(value="1.0")
        self.type_var = tk.StringVar(value="PK")

        def field(label, var, w):
            tk.Label(ctrl, text=label, bg=BG, fg=MUTED,
                     font=(FONT, 9)).pack(side="left", padx=(6, 3))
            e = tk.Entry(ctrl, textvariable=var, width=w, bg=CARD, fg=TEXT,
                         insertbackground=TEXT, relief="flat", font=(FONT, 9))
            e.pack(side="left", ipady=3)
            e.bind("<Return>", lambda ev: self.apply_fields())
            e.bind("<FocusOut>", lambda ev: self.apply_fields())
            return e

        field("Preamp", self.preamp_var, 7)
        tk.Label(ctrl, text=" 类型", bg=BG, fg=MUTED,
                 font=(FONT, 9)).pack(side="left", padx=(8, 3))
        menu = tk.OptionMenu(ctrl, self.type_var, "PK", "LS", "HS",
                             command=lambda _v: self.apply_fields())
        menu.configure(bg=CARD, fg=TEXT, activebackground=HOVER,
                       relief="flat", highlightthickness=0,
                       font=(FONT, 9), width=3)
        menu["menu"].configure(bg=CARD, fg=TEXT)
        menu.pack(side="left")

        field("Fc", self.fc_var, 8)
        field("Gain", self.gain_var, 7)
        field("Q", self.q_var, 6)

        self.canvas = tk.Canvas(self, bg=CARD, highlightthickness=0, bd=0,
                                height=330)
        self.canvas.pack(fill="both", expand=True, padx=14, pady=(4, 6))
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", None))
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", lambda e: self._clear_cursor())

        bottom = tk.Frame(self, bg=BG)
        bottom.pack(fill="x", padx=14, pady=(0, 12))
        self.preview_toggle = ToggleChip(bottom, "实时预览", value=False,
                                         command=self._toggle_preview, width=88)
        self.preview_toggle.pack(side="left", padx=(0, 8))
        RoundedButton(bottom, "添加频点", self.add_band, kind="ghost",
                      width=92, height=32).pack(side="left")
        RoundedButton(bottom, "删除频点", self.del_band, kind="ghost",
                      width=92, height=32).pack(side="left", padx=6)
        RoundedButton(bottom, "保存为预设", self.save, kind="primary",
                      width=104, height=32).pack(side="left", padx=(6, 0))
        RoundedButton(bottom, "关闭", self._close, kind="ghost",
                      width=72, height=32).pack(side="right")
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.status = tk.Label(self, text="拖动圆点改频率/增益；滚轮调 Q。",
                               bg=BG, fg=MUTED, anchor="w", font=(FONT, 9))
        self.status.pack(fill="x", padx=16, pady=(0, 8))

        if self.filters:
            self.selected = 0
            self.redraw()
        elif not self.graphic:
            self.add_band()
        else:
            self.redraw()
        self.after(80, lambda: set_dark_titlebar(
            self, bool(getattr(self.app, "dark", PALETTE is DARK))))

    # ---------- 坐标 ----------
    def _plot_rect(self):
        w = max(200, self.canvas.winfo_width())
        h = max(160, self.canvas.winfo_height())
        return (self.LEFT, self.TOP, w - self.RIGHT, h - self.BOTTOM)

    def f_to_x(self, f):
        left, top, right, bottom = self._plot_rect()
        ratio = math.log(max(20.0, f) / 20.0) / math.log(20000.0 / 20.0)
        return left + ratio * (right - left)

    def x_to_f(self, x):
        left, top, right, bottom = self._plot_rect()
        ratio = (x - left) / max(1, right - left)
        return 20.0 * (1000.0 ** max(0.0, min(1.0, ratio)))

    def g_to_y(self, g):
        left, top, right, bottom = self._plot_rect()
        ratio = (self.DB_RANGE - max(-self.DB_RANGE, min(self.DB_RANGE, g))) / (2 * self.DB_RANGE)
        return top + ratio * (bottom - top)

    def y_to_g(self, y):
        left, top, right, bottom = self._plot_rect()
        ratio = (y - top) / max(1, bottom - top)
        return self.DB_RANGE - max(0.0, min(1.0, ratio)) * 2 * self.DB_RANGE

    # ---------- 绘制 ----------
    def redraw(self):
        c = self.canvas
        try:
            c.configure(bg=CARD)
        except Exception:
            pass
        c.delete("all")
        left, top, right, bottom = self._plot_rect()
        c.create_rectangle(left, top, right, bottom, outline=BORDER, tags="border")
        for f in (20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000):
            x = self.f_to_x(f)
            c.create_line(x, top, x, bottom, fill=GRID, tags="grid")
            label = ("%gk" % (f / 1000.0)) if f >= 1000 else str(f)
            c.create_text(x, bottom + 12, text=label, fill=MUTED,
                          font=(FONT, 8), tags="gridtext")
        for db in range(-12, 13, 3):
            y = self.g_to_y(db)
            c.create_line(left, y, right, y, fill=GRID, tags="grid")
            c.create_text(left - 18, y, text="%+d" % db, fill=MUTED,
                          font=(FONT, 8), tags="gridtext")
        c.create_line(left, self.g_to_y(0), right, self.g_to_y(0),
                      fill=AXIS, tags="axis")
        freqs, gains = response_curve(self.preamp, self.filters, self.graphic)
        pts = []
        for f, g in zip(freqs, gains):
            pts.extend((self.f_to_x(f), self.g_to_y(g)))
        if len(pts) >= 4:
            c.create_line(*pts, fill=ACCENT, width=2, tags="curve")
        for i, flt in enumerate(self.filters):
            x = self.f_to_x(flt["f"])
            y = self.g_to_y(flt["g"])
            r = 6 if i == self.selected else 5
            c.create_oval(x - r, y - r, x + r, y + r,
                          fill=ACCENT, outline=RED if i == self.selected else CARD,
                          width=2 if i == self.selected else 1, tags="point")
            c.create_text(x, y - 12, text=str(i + 1), fill=TEXT,
                          font=(FONT, 8, "bold"), tags="pointtext")
        self._draw_cursor()
        self.update_fields()

    def theme_frame(self):
        try:
            self.canvas.configure(bg=CARD)
            self.canvas.itemconfigure("border", outline=BORDER)
            self.canvas.itemconfigure("grid", fill=GRID)
            self.canvas.itemconfigure("gridtext", fill=MUTED)
            self.canvas.itemconfigure("axis", fill=AXIS)
            self.canvas.itemconfigure("curve", fill=ACCENT)
            self.canvas.itemconfigure("point", fill=ACCENT)
            self.canvas.itemconfigure("pointtext", fill=TEXT)
            if 0 <= self.selected < len(self.filters):
                flt = self.filters[self.selected]
                x, y = self.f_to_x(flt["f"]), self.g_to_y(flt["g"])
                for item in self.canvas.find_withtag("point"):
                    coords = self.canvas.coords(item)
                    if coords and abs((coords[0] + coords[2]) / 2 - x) < 2:
                        self.canvas.itemconfigure(item, outline=RED)
        except Exception:
            pass

    def _draw(self):
        self.redraw()

    def update_fields(self):
        if 0 <= self.selected < len(self.filters):
            f = self.filters[self.selected]
            self.type_var.set(f["type"])
            self.fc_var.set("%.0f" % f["f"])
            self.gain_var.set("%.1f" % f["g"])
            self.q_var.set("%.2f" % f["q"])
        self.preamp_var.set("%.1f" % self.preamp)

    # ---------- 交互 ----------
    def on_press(self, event):
        best, best_d = -1, 14.0
        for i, flt in enumerate(self.filters):
            dx = self.f_to_x(flt["f"]) - event.x
            dy = self.g_to_y(flt["g"]) - event.y
            d = math.hypot(dx, dy)
            if d < best_d:
                best, best_d = i, d
        self.selected = best
        self.drag = best if best >= 0 else None
        self.redraw()

    def on_drag(self, event):
        if self.drag is None or not (0 <= self.drag < len(self.filters)):
            return
        flt = self.filters[self.drag]
        flt["f"] = max(20.0, min(20000.0, self.x_to_f(event.x)))
        flt["g"] = max(-12.0, min(12.0, self.y_to_g(event.y)))
        self.redraw()
        self._schedule_preview()

    def on_wheel(self, event):
        if not (0 <= self.selected < len(self.filters)):
            return
        flt = self.filters[self.selected]
        factor = 1.12 if event.delta > 0 else 1 / 1.12
        flt["q"] = max(0.1, min(20.0, flt["q"] * factor))
        self.redraw()
        self._schedule_preview()

    def apply_fields(self):
        try:
            self.preamp = float(self.preamp_var.get())
        except ValueError:
            pass
        if 0 <= self.selected < len(self.filters):
            flt = self.filters[self.selected]
            flt["type"] = self.type_var.get() or "PK"
            try:
                flt["f"] = max(20.0, min(20000.0, float(self.fc_var.get())))
                flt["g"] = max(-12.0, min(12.0, float(self.gain_var.get())))
                flt["q"] = max(0.1, min(20.0, float(self.q_var.get())))
            except ValueError:
                pass
        self.redraw()
        self._schedule_preview()

    def _fmt_freq(self, f):
        if f >= 1000.0:
            return "%.2f kHz" % (f / 1000.0)
        return "%.0f Hz" % f

    def _draw_cursor(self):
        c = self.canvas
        c.delete("cursor")
        if not self._cursor:
            return
        left, top, right, bottom = self._plot_rect()
        x, y = self._cursor
        if not (left <= x <= right and top <= y <= bottom):
            return
        c.create_line(x, top, x, bottom, fill=AXIS, dash=(2, 4), tags="cursor")
        c.create_line(left, y, right, y, fill=AXIS, dash=(2, 4), tags="cursor")
        label = "%s   %+.1f dB" % (self._fmt_freq(self.x_to_f(x)),
                                    self.y_to_g(y))
        tx = x + 10 if x < right - 110 else x - 10
        anchor = "nw" if x < right - 110 else "ne"
        c.create_text(tx, top + 8, text=label, fill=TEXT, anchor=anchor,
                      font=(FONT, 8, "bold"), tags="cursor")

    def _clear_cursor(self):
        self._cursor = None
        self.canvas.delete("cursor")

    def on_motion(self, event):
        self._cursor = (event.x, event.y)
        self._draw_cursor()

    def _next_band_frequency(self):
        if not self.filters:
            return 1000.0
        order = [1000.0, 100.0, 10000.0, 250.0, 3000.0, 40.0, 6000.0,
                 160.0, 2000.0, 500.0, 8000.0, 63.0, 400.0, 5000.0,
                 12000.0, 30.0, 15000.0]
        used = [flt["f"] for flt in self.filters]

        def distance(f):
            return min(abs(math.log(f / u)) for u in used)

        for f in order:
            if distance(f) > 0.22:
                return f
        candidates = [30.0 * (533.33 ** (i / 24.0)) for i in range(25)]
        return float(max(candidates, key=distance))

    def add_band(self):
        self.filters.append({"type": "PK", "f": self._next_band_frequency(),
                             "g": 0.0, "q": 1.0})
        self.selected = len(self.filters) - 1
        self.redraw()
        self._schedule_preview()

    def del_band(self):
        if 0 <= self.selected < len(self.filters):
            self.filters.pop(self.selected)
            self.selected = min(self.selected, len(self.filters) - 1)
            self.redraw()
            self._schedule_preview()

    def _serialize(self):
        lines = ["Preamp: %.1f dB" % self.preamp]
        for i, flt in enumerate(self.filters, 1):
            lines.append("Filter %d: ON %s Fc %.0f Hz Gain %.1f dB Q %.2f"
                         % (i, flt["type"], flt["f"], flt["g"], flt["q"]))
        if self.graphic:
            parts = ["%g %g" % (f, g) for f, g in sorted(self.graphic)]
            lines.append("GraphicEQ: " + "; ".join(parts))
        return "\n".join(lines) + "\n"

    def _toggle_preview(self):
        if self.preview_toggle.get():
            if not self.app or not getattr(self.app, "admin", False):
                messagebox.showwarning("需要管理员权限",
                                       "实时预览需要管理员权限，请点「以管理员重启」。",
                                       parent=self)
                self.preview_toggle.value = False
                self.preview_toggle._draw()
                return
            self.restore_fn = getattr(self.app, "active_fn", None)
            self.previewing = True
            self._push_preview()
        else:
            self.previewing = False
            self._restore()

    def _schedule_preview(self):
        if not self.previewing:
            return
        try:
            if self._preview_job:
                self.after_cancel(self._preview_job)
        except Exception:
            pass
        self._preview_job = self.after(120, self._push_preview)

    def _push_preview(self):
        self._preview_job = None
        if not self.previewing or not self.app:
            return
        ok = self.app.preview_preset(self._serialize())
        if not ok:
            self.previewing = False
            self.preview_toggle.value = False
            self.preview_toggle._draw()

    def _restore(self):
        if not self.app:
            return
        try:
            if self.restore_fn:
                self.app.apply(self.restore_fn)
            else:
                self.app.bypass()
        except Exception:
            pass

    def _close(self):
        self.previewing = False
        self._restore()
        self.destroy()

    def _ask_name(self):
        initial = (os.path.splitext(self.target_fn)[0] if self.target_fn
                   else "peq")
        top = tk.Toplevel(self)
        top.title("保存预设")
        top.configure(bg=BG)
        top.transient(self)
        top.attributes("-topmost", True)
        top.resizable(False, False)
        w, h = 380, 190
        x = self.winfo_rootx() + (self.winfo_width() - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 2
        top.geometry("%dx%d+%d+%d" % (w, h, x, y))

        tk.Label(top, text="预设名称", bg=BG, fg=TEXT,
                 font=(FONT, 11, "bold")).pack(anchor="w", padx=20, pady=(18, 6))
        entry = tk.Entry(top, bg=CARD, fg=TEXT, insertbackground=TEXT,
                         relief="flat", font=(FONT, 11),
                         highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=ACCENT)
        entry.pack(fill="x", padx=20, ipady=6)
        entry.insert(0, initial)
        entry.select_range(0, "end")
        hint = tk.Label(top, text="保存到：%s" % EQ_DIR, bg=BG, fg=MUTED,
                        font=(FONT, 8), anchor="w")
        hint.pack(fill="x", padx=20, pady=(6, 0))

        result = {"value": None}

        def submit(_e=None):
            name = entry.get().strip()
            if not name:
                return
            result["value"] = name
            top.destroy()

        def cancel(_e=None):
            top.destroy()

        row = tk.Frame(top, bg=BG)
        row.pack(fill="x", padx=20, pady=(16, 16))
        RoundedButton(row, "保存", submit, kind="primary",
                      width=96, height=34).pack(side="right")
        RoundedButton(row, "取消", cancel, kind="ghost",
                      width=80, height=34).pack(side="right", padx=(0, 8))
        entry.bind("<Return>", submit)
        top.bind("<Escape>", cancel)
        entry.focus_set()
        top.grab_set()
        self.wait_window(top)
        return result["value"]

    def save(self):
        name = self._ask_name()
        if not name:
            return
        text = self._serialize()
        os.makedirs(EQ_DIR, exist_ok=True)
        filename = safe_preset_name(name, "peq") + ".txt"
        path = os.path.join(EQ_DIR, filename)
        overwrite = (self.target_fn is not None and filename == self.target_fn)
        if os.path.exists(path) and not overwrite:
            base, ext = os.path.splitext(filename)
            n = 2
            while os.path.exists(os.path.join(EQ_DIR, "%s-%d%s" % (base, n, ext))):
                n += 1
            filename = "%s-%d%s" % (base, n, ext)
            path = os.path.join(EQ_DIR, filename)
        if overwrite:
            try:
                shutil.copy2(path, path + ".bak")
            except OSError:
                pass
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        except OSError as exc:
            self.status.configure(text="保存失败：%s" % exc, fg=RED)
            return
        self.status.configure(text="已保存：%s" % filename, fg=GREEN)
        if self.previewing:
            self.previewing = False
            self._restore()
            if self.app and getattr(self.app, "admin", False):
                try:
                    self.app.apply(filename)
                except Exception:
                    pass
        if self.on_saved:
            try:
                self.on_saved()
            except Exception:
                pass


class OpraBrowser(tk.Toplevel):
    """从 OPRA 数据库搜索耳机并生成 Equalizer APO 预设。"""

    def __init__(self, master, on_import=None):
        super().__init__(master)
        self.on_import = on_import
        self.title("耳机库 · OPRA")
        self.configure(bg=BG)
        self.geometry("620x480+%d+%d" % (master.winfo_rootx() + 160,
                                         master.winfo_rooty() + 120))
        self.transient(master)
        self.attributes("-topmost", True)
        self.vendors = {}
        self.products = {}
        self.eqs = {}
        self.matches = []
        self._busy = False
        self._queue = queue.Queue()

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 8))
        self.entry = tk.Entry(top, bg=CARD, fg=TEXT, insertbackground=TEXT,
                              relief="flat", font=(FONT, 10))
        self.entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.entry.bind("<Return>", lambda e: self.search())
        RoundedButton(top, "搜索", self.search, kind="primary",
                      width=72, height=32).pack(side="left", padx=(8, 0))
        RoundedButton(top, "刷新库", self.refresh_db, kind="ghost",
                      width=76, height=32).pack(side="left", padx=(6, 0))

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16)
        self.listbox = tk.Listbox(body, bg=CARD, fg=TEXT, selectbackground=ACCENT,
                                  selectforeground="#ffffff", relief="flat",
                                  highlightthickness=0, font=(FONT, 10),
                                  activestyle="none")
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll = tk.Scrollbar(body, command=self.listbox.yview)
        scroll.pack(side="left", fill="y")
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.bind("<<ListboxSelect>>", lambda e: self.show_detail())
        self.listbox.bind("<Double-Button-1>", lambda e: self.import_selected())

        self.progress = tk.Canvas(self, height=6, bg=BG,
                                  highlightthickness=0, bd=0)
        self.progress.pack(fill="x", padx=16, pady=(6, 0))
        self.detail = tk.Label(self, text="", bg=BG, fg=MUTED, anchor="w",
                               justify="left", font=(FONT, 9))
        self.detail.pack(fill="x", padx=16, pady=(8, 4))
        self.status = tk.Label(self, text="", bg=BG, fg=ACCENT, anchor="w",
                               font=(FONT, 9))
        self.status.pack(fill="x", padx=16)

        bottom = tk.Frame(self, bg=BG)
        bottom.pack(fill="x", padx=16, pady=12)
        RoundedButton(bottom, "导入为预设", self.import_selected,
                      kind="primary", width=108, height=34).pack(side="left")
        RoundedButton(bottom, "关闭", self.destroy, kind="ghost",
                      width=80, height=34).pack(side="right")

        self.after(60, self.start)
        self.after(90, lambda: set_dark_titlebar(self, PALETTE is DARK))

    def start(self):
        if not os.path.exists(OPRA_CACHE):
            if not messagebox.askyesno(
                    "下载耳机库",
                    "首次使用需要下载 OPRA 数据库（约 12 MB）。\n\n"
                    "下载后保存在程序目录，之后可离线使用。\n现在下载吗？",
                    parent=self):
                self.status.configure(text="未下载数据库，无法搜索。")
                return
            self._download_async()
            return
        self.reload()

    def reload(self):
        try:
            self.vendors, self.products, self.eqs = load_opra_database()
        except Exception as exc:  # noqa: BLE001
            self.status.configure(text="读取失败：%s" % exc)
            return
        self.status.configure(
            text="共 %d 个型号，%d 条 EQ。输入型号后回车搜索。"
                 % (len(self.products), sum(len(v) for v in self.eqs.values())))
        self.search()

    def refresh_db(self):
        if self._busy:
            return
        if not messagebox.askyesno("刷新耳机库", "重新下载 OPRA 数据库？", parent=self):
            return
        self._download_async()

    def _draw_progress(self, fraction=None):
        c = self.progress
        c.delete("all")
        w = max(1, c.winfo_width())
        c.create_rectangle(0, 2, w, 5, fill=BORDER, outline="")
        if fraction is None:
            phase = (time.time() * 0.7) % 1.0
            x0 = max(0.0, phase - 0.22)
            c.create_rectangle(int(w * x0), 2, int(w * phase), 5,
                               fill=ACCENT, outline="")
        else:
            fraction = max(0.0, min(1.0, fraction))
            c.create_rectangle(0, 2, int(w * fraction), 5,
                               fill=ACCENT, outline="")

    def _set_busy(self, busy):
        self._busy = busy
        if busy:
            self._draw_progress(None)
            self.after(80, self._poll_queue)
        else:
            self.progress.delete("all")

    def _download_async(self):
        if self._busy:
            return
        self._set_busy(True)
        self.status.configure(text="正在下载数据库…")

        def work():
            try:
                download_opra_database(
                    lambda done, total: self._queue.put(("progress", done, total)))
                self._queue.put(("done",))
            except Exception as exc:  # noqa: BLE001
                self._queue.put(("error", str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _poll_queue(self):
        if not self.winfo_exists():
            return
        try:
            while True:
                msg = self._queue.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    done, total = msg[1], msg[2]
                    if total:
                        self._draw_progress(done / total)
                        self.status.configure(
                            text="正在下载数据库… %d%%（%.1f MB）"
                                 % (int(done * 100 / total), done / 1024 ** 2))
                    else:
                        self._draw_progress(None)
                        self.status.configure(
                            text="正在下载数据库… %.1f MB" % (done / 1024 ** 2))
                elif kind == "done":
                    self._set_busy(False)
                    self.reload()
                elif kind == "error":
                    self._set_busy(False)
                    self.status.configure(text="下载失败：%s" % msg[1])
        except queue.Empty:
            pass
        if self._busy:
            self._draw_progress(None)
            self.after(80, self._poll_queue)

    def _vendor_name(self, vendor_id):
        return (self.vendors.get(vendor_id) or {}).get("name", vendor_id or "")

    def _local_presets(self, tokens):
        rows = []
        seen = set()
        dirs = [EQ_DIR]
        bundled = _bundled_dir("presets")
        if bundled and os.path.abspath(bundled) != os.path.abspath(EQ_DIR):
            dirs.append(bundled)
        for folder in dirs:
            try:
                names = sorted(os.listdir(folder))
            except OSError:
                continue
            for name in names:
                if not name.lower().endswith(".txt") or name in seen:
                    continue
                label = NAME_MAP.get(name, os.path.splitext(name)[0])
                haystack = (label + " " + name).lower()
                if tokens and not all(tok in haystack for tok in tokens):
                    continue
                seen.add(name)
                rows.append((folder, name, label))
        return rows

    def search(self):
        if self._busy:
            return
        query = self.entry.get().strip().lower()
        self.listbox.delete(0, "end")
        self.matches = []
        self.local_rows = []
        tokens = [x for x in query.split() if x]
        for pid, product in self.products.items():
            name = product.get("name", "")
            vendor = self._vendor_name(product.get("vendor_id"))
            haystack = ("%s %s" % (vendor, name)).lower()
            if tokens and not all(tok in haystack for tok in tokens):
                continue
            if pid not in self.eqs:
                continue
            self.matches.append((pid, vendor, name, len(self.eqs[pid])))
        self.matches.sort(key=lambda x: (x[1].lower(), x[2].lower()))
        for pid, vendor, name, count in self.matches:
            self.listbox.insert("end", "%s · %s  (%d)" % (vendor, name, count))
        self.local_rows = self._local_presets(tokens)
        for folder, name, label in self.local_rows:
            self.listbox.insert("end", "[本地] %s" % label)
        total = len(self.matches) + len(self.local_rows)
        self.status.configure(
            text="找到 %d 个在线型号，%d 个本地预设。" % (len(self.matches), len(self.local_rows)))
        if total:
            self.listbox.selection_set(0)
            self.show_detail()

    def _selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return None
        idx = sel[0]
        if idx < len(self.matches):
            return ("opra", self.matches[idx])
        local_idx = idx - len(self.matches)
        if 0 <= local_idx < len(self.local_rows):
            return ("local", self.local_rows[local_idx])
        return None

    def show_detail(self):
        item = self._selected()
        if not item:
            return
        kind, data = item
        if kind == "opra":
            pid, vendor, name, count = data
            eqs = self.eqs.get(pid) or []
            authors = ", ".join(sorted({(e.get("author") or "?") for e in eqs}))
            self.detail.configure(text="%s · %s\nEQ 来源：%s" % (vendor, name, authors))
        else:
            folder, name, label = data
            self.detail.configure(text="本地预设：%s\n位置：%s" % (label, folder))

    def import_selected(self):
        if self._busy:
            return
        item = self._selected()
        if not item:
            self.status.configure(text="先选一个型号。")
            return
        kind, data = item
        if kind == "local":
            folder, name, label = data
            src = os.path.join(folder, name)
            dst = os.path.join(EQ_DIR, name)
            try:
                os.makedirs(EQ_DIR, exist_ok=True)
                if os.path.abspath(src) != os.path.abspath(dst) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
                self.status.configure(text="本地预设已在列表：%s" % name)
            except OSError as exc:
                self.status.configure(text="导入失败：%s" % exc)
                return
            if self.on_import:
                self.on_import()
            return
        pid, vendor, name, count = data
        eqs = self.eqs.get(pid) or []
        eq = next((e for e in eqs if "autoeq" in (e.get("author") or "").lower()),
                  eqs[0])
        text = opra_to_preset(eq)
        filename = safe_preset_name("opra-%s-%s" % (vendor, name), "opra-preset") + ".txt"
        os.makedirs(EQ_DIR, exist_ok=True)
        path = os.path.join(EQ_DIR, filename)
        if os.path.exists(path):
            base, ext = os.path.splitext(filename)
            n = 2
            while os.path.exists(os.path.join(EQ_DIR, "%s-%d%s" % (base, n, ext))):
                n += 1
            filename = "%s-%d%s" % (base, n, ext)
            path = os.path.join(EQ_DIR, filename)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        except OSError as exc:
            self.status.configure(text="写入失败：%s" % exc)
            return
        self.status.configure(text="已导入：%s" % filename)
        if self.on_import:
            try:
                self.on_import()
            except Exception:
                pass

class App:
    def __init__(self, root):
        self.root = root
        self.admin = is_admin()
        root.title("EQ 切换器")
        root.configure(bg=BG)
        ico = resource_path("eq.ico")
        if ico:
            try:
                root.iconbitmap(default=ico)
            except Exception:
                pass
        _pending_geo = getattr(self, "_pending_geometry", None)
        root.geometry(_pending_geo or "940x700+120+80")
        root.minsize(860, 600)
        self.ui_state = load_ui_state()
        _theme = self.ui_state.get("theme")
        self.dark = True if _theme is None else (_theme == "dark")
        apply_palette(self.dark)
        root.configure(bg=BG)
        set_dark_titlebar(root, self.dark)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.pinned = bool(self.ui_state.get("topmost", True))
        self.active_fn = None
        self.volume_match = bool(self.ui_state.get("volume_match", True))
        root.attributes("-topmost", self.pinned)

        self._build_ui()

    def _build_ui(self, parent=None):
        if parent is None:
            self.container = tk.Frame(self.root, bg=BG)
            self.container.pack(fill="both", expand=True)
            parent = self.container
        else:
            self.container = parent
        root = parent

        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=20, pady=(18, 6))
        left = tk.Frame(header, bg=BG)
        left.pack(side="left")
        tk.Label(left, text="EQ 切换器", bg=BG, fg=TEXT,
                 font=(FONT, 22, "bold")).pack(anchor="w")
        tk.Label(left, text="Equalizer APO 预设切换 · FiiO K11",
                 bg=BG, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(3, 0))
        right = tk.Frame(header, bg=BG)
        right.pack(side="right", anchor="n")
        tk.Label(right, text="v2.0.1", bg=BG, fg=MUTED,
                 font=(FONT, 8)).pack(anchor="e")
        self.mode = tk.Label(right, text="管理员" if self.admin else "普通模式",
                             bg=GREEN if self.admin else ORANGE_SOFT,
                             fg="#ffffff" if self.admin else ORANGE,
                             font=(FONT, 8), padx=8, pady=2)
        self.mode.pack(anchor="e", pady=(4, 0))
        self.pin = PinButton(right, value=self.pinned, command=self._toggle_pin)
        self.pin.pack(anchor="e", pady=(4, 0))
        self.theme_switch = ThemeSwitch(right, value=self.dark,
                                        command=self._toggle_theme)
        self.theme_switch.pack(anchor="e", pady=(4, 0))

        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        leftcol = tk.Frame(body, bg=BG)
        leftcol.pack(side="left", fill="both", expand=True)
        rightcol = tk.Frame(body, bg=BG)
        rightcol.pack(side="left", fill="both", expand=True, padx=(14, 0))

        devsel = tk.Frame(leftcol, bg=BG)
        devsel.pack(fill="x", pady=(0, 10))
        tk.Label(devsel, text="作用设备", bg=BG, fg=MUTED,
                 font=(FONT, 9)).pack(side="left")
        self.devices = list_output_devices()
        self._device_map = {label: pattern for _a, label, pattern, _g in self.devices}
        self._device_labels_all = [label for _a, label, _p, _g in self.devices]
        self._device_labels_active = [label for a, label, _p, _g in self.devices if a]
        self.show_offline = tk.BooleanVar(value=False)
        opts = ["全部设备（不限定）"] + self._device_labels_active
        self.device_combo = DeviceSelector(devsel, opts, width=262)
        self.device_combo.pack(side="left", padx=(8, 0))
        self.device_combo.on_change = self._on_device
        self.offline_chip = ToggleChip(devsel, "含未连接",
                                       value=self.show_offline.get(),
                                       command=self._toggle_offline,
                                       width=86, height=32)
        self.offline_chip.pack(side="left", padx=(8, 0))
        self.device_combo.set_options(opts)
        _dev, _inc = read_config_state()
        self._select_device_from_config(_dev)

        self.list_card = Card(leftcol)
        self.list_card.pack(fill="both", expand=True)
        holder = tk.Frame(self.list_card.body, bg=CARD)
        holder.pack(fill="both", expand=True)
        self.list_canvas = tk.Canvas(holder, bg=CARD, highlightthickness=0, bd=0)
        self._list_vsb = tk.Scrollbar(holder, orient="vertical",
                                      command=self.list_canvas.yview)
        self.list_canvas.configure(yscrollcommand=self._on_list_scroll)
        self.list_canvas.pack(side="left", fill="both", expand=True)
        self.frame = tk.Frame(self.list_canvas, bg=CARD)
        self._list_win = self.list_canvas.create_window((0, 0), window=self.frame,
                                                        anchor="nw")
        self.frame.bind("<Configure>",
                        lambda e: self.list_canvas.configure(
                            scrollregion=self.list_canvas.bbox("all")))
        self.list_canvas.bind("<Configure>",
                              lambda e: self.list_canvas.itemconfigure(
                                  self._list_win, width=e.width))
        self.list_canvas.bind_all("<MouseWheel>", self._on_wheel)
        self._list_vsb.pack_forget()

        self.analysis_card = Card(rightcol)
        self.analysis_card.pack(fill="both", expand=True)
        ab = self.analysis_card.body
        tk.Label(ab, text="分析面板", bg=CARD, fg=MUTED,
                 font=(FONT, 8, "bold")).pack(anchor="w", padx=10, pady=(0, 4))
        self.graph = tk.Canvas(ab, bg=CARD, highlightthickness=0, bd=0,
                               height=320)
        self.graph.pack(fill="both", expand=True, padx=6)
        self.graph.bind("<Configure>", lambda e: self._draw_analysis())
        stats = tk.Frame(ab, bg=CARD)
        stats.pack(fill="x", padx=10, pady=(6, 2))
        self.stat_peak = tk.Label(stats, text="峰值增益  —", bg=CARD, fg=TEXT,
                                  font=(FONT, 9), anchor="w")
        self.stat_peak.pack(anchor="w")
        self.stat_filters = tk.Label(stats, text="滤波器  —", bg=CARD, fg=MUTED,
                                     font=(FONT, 9), anchor="w")
        self.stat_filters.pack(anchor="w")
        self.stat_preamp = tk.Label(stats, text="预增益  —", bg=CARD, fg=MUTED,
                                    font=(FONT, 9), anchor="w")
        self.stat_preamp.pack(anchor="w")

        self.banner = tk.Label(root, text="", bg=BG, fg=ORANGE,
                               font=(FONT, 9), wraplength=430, justify="left")
        self.banner.pack(fill="x", padx=22)

        bottom = tk.Frame(root, bg=BG)
        bottom.pack(fill="x", padx=20, pady=(4, 8))
        self.volume_toggle = ToggleChip(
            bottom, "音量匹配", value=self.volume_match,
            command=self._toggle_volume_match, width=88)
        self.volume_toggle.pack(side="left", padx=(0, 8))
        RoundedButton(bottom, "PEQ 编辑器", self.open_peq, kind="ghost",
                      width=104).pack(side="left", padx=(0, 8))
        RoundedButton(bottom, "耳机库", self.open_opra, kind="ghost",
                      width=96).pack(side="left")
        RoundedButton(bottom, "添加预设", self.add_presets, kind="ghost",
                      width=96).pack(side="left", padx=8)
        RoundedButton(bottom, "刷新列表", self.build, kind="ghost",
                      width=96).pack(side="left", padx=8)
        RoundedButton(bottom, "关闭 EQ", self.bypass, kind="danger",
                      width=96).pack(side="left")
        if not self.admin:
            RoundedButton(bottom, "以管理员重启", relaunch_as_admin,
                          kind="primary", width=128).pack(side="right")

        self.status = tk.Label(root, text="", bg=BG, fg=MUTED,
                               font=(FONT, 9), anchor="w")
        self.status.pack(fill="x", padx=22, pady=(0, 14))

        self.build()
        self._theme_roles = None
        self.root.after(80, lambda: set_dark_titlebar(self.root, self.dark))

    # ---------- 逻辑 ----------
    def read_active(self):
        return read_config_state()[1]

    def _select_device_from_config(self, device_line):
        label = "全部设备（不限定）"
        if device_line:
            low = device_line.lower()
            for _active, lab, _pattern, guid in self.devices:
                if guid and guid.lower() in low:
                    label = lab
                    break
        if label not in self.device_combo.options:
            self.device_combo.set_options(
                self.device_combo.options + [label], keep=label)
        else:
            self.device_combo.set(label)

    def _toggle_theme(self):
        dark = self.theme_switch.get()
        self.ui_state["theme"] = "dark" if dark else "light"
        save_ui_state(self.ui_state)
        self.dark = dark
        set_dark_titlebar(self.root, dark)
        for w in self.root.winfo_children():
            if isinstance(w, tk.Toplevel):
                set_dark_titlebar(w, dark)
        self._animate_theme(DARK if dark else LIGHT)

    def _collect_theme_targets(self):
        opts = ("background", "foreground", "activebackground",
                "activeforeground", "selectbackground", "selectforeground",
                "highlightbackground", "highlightcolor", "insertbackground")
        roles = []
        canvases = []
        cards = []
        dialogs = []

        def collect(widget):
            try:
                children = widget.winfo_children()
            except Exception:
                return
            for child in children:
                if isinstance(child, tk.Toplevel) and hasattr(child, "theme_frame"):
                    dialogs.append(child)
                for opt in opts:
                    try:
                        value = child.cget(opt)
                    except Exception:
                        continue
                    if not value:
                        continue
                    key = resolve_color_key(value, opt)
                    if key:
                        roles.append((child, opt, key))
                if isinstance(child, tk.Canvas):
                    canvases.append(child)
                if isinstance(child, Card):
                    cards.append(child)
                collect(child)

        collect(self.root)
        self._theme_roles = roles
        self._theme_canvases = canvases
        self._theme_cards = cards
        self._theme_dialogs = dialogs

    def _apply_palette_to_widgets(self, target):
        opts = ("background", "foreground", "activebackground",
                "activeforeground", "selectbackground", "selectforeground",
                "highlightbackground", "highlightcolor", "insertbackground")

        def walk(widget):
            try:
                children = widget.winfo_children()
            except Exception:
                return
            for child in children:
                for opt in opts:
                    try:
                        value = child.cget(opt)
                    except Exception:
                        continue
                    if not value:
                        continue
                    key = resolve_color_key(value, opt)
                    if key and key in target:
                        try:
                            child.configure(**{opt: target[key]})
                        except Exception:
                            pass
                walk(child)

        walk(self.root)

    def _redraw_all_canvases(self):
        def walk(widget):
            try:
                children = widget.winfo_children()
            except Exception:
                return
            for child in children:
                if isinstance(child, tk.Toplevel) and hasattr(child, "_draw"):
                    try:
                        child._draw()
                    except Exception:
                        pass
                if isinstance(child, tk.Canvas):
                    drawable = hasattr(child, "_draw") or hasattr(child, "_redraw")
                    if drawable:
                        try:
                            child.configure(bg=child.master.cget("background"))
                        except Exception:
                            pass
                        try:
                            if hasattr(child, "_draw"):
                                child._draw()
                            elif hasattr(child, "_redraw"):
                                child._redraw()
                        except Exception:
                            pass
                walk(child)

        walk(self.root)
        for card in getattr(self, "_theme_cards", []):
            try:
                card.canvas.configure(bg=BG)
                card._redraw()
            except Exception:
                pass
        try:
            self.graph.configure(bg=CARD)
            self._draw_analysis()
        except Exception:
            pass

    def _animate_theme(self, target, duration=0.5):
        if getattr(self, "_animating", False):
            return
        if getattr(self, "_theme_roles", None) is None:
            self._collect_theme_targets()
        self._animating = True
        start_pal = dict(PALETTE)
        roles = list(self._theme_roles)
        canvases = list(self._theme_canvases)
        cards = list(self._theme_cards)
        dialogs = list(getattr(self, "_theme_dialogs", []))
        started = time.monotonic()

        def ease(x):
            return x * x * (3 - 2 * x)

        def frame():
            elapsed = time.monotonic() - started
            t = min(1.0, elapsed / duration)
            pal = {k: lerp_hex(start_pal[k], target[k], ease(t)) for k in target}
            set_palette_values(pal)
            try:
                self.root.configure(bg=BG)
            except Exception:
                pass
            for widget, opt, key in roles:
                try:
                    widget.configure(**{opt: pal[key]})
                except Exception:
                    continue
            for canvas in canvases:
                try:
                    if hasattr(canvas, "_draw"):
                        canvas._draw()
                    elif hasattr(canvas, "_redraw"):
                        canvas._redraw()
                except Exception:
                    pass
            for card in cards:
                try:
                    card.canvas.configure(bg=BG)
                    card._redraw()
                except Exception:
                    pass
            for dlg in dialogs:
                try:
                    dlg.theme_frame()
                except Exception:
                    pass
            try:
                self.graph.itemconfigure("abg", fill=CARD)
                self.graph.itemconfigure("agrid", fill=GRID)
                self.graph.itemconfigure("aaxis", fill=AXIS)
                self.graph.itemconfigure("acurve", fill=ACCENT)
            except Exception:
                pass
            if t < 1.0:
                self.root.after(16, frame)
                return
            set_palette_values(dict(target))
            self._apply_palette_to_widgets(target)
            self._redraw_all_canvases()
            for dlg in dialogs:
                try:
                    dlg.theme_frame()
                except Exception:
                    pass
            self._theme_roles = None
            self._animating = False
            if getattr(self, "_pending_build", False):
                self._pending_build = False
                try:
                    self.build()
                except Exception:
                    pass

        frame()

    def _on_close(self):
        self._animating = False
        try:
            self.root.unbind_all("<MouseWheel>")
        except Exception:
            pass
        for w in list(self.root.winfo_children()):
            if isinstance(w, tk.Toplevel):
                try:
                    w.destroy()
                except Exception:
                    pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def _toggle_pin(self):
        self.pinned = self.pin.get()
        self.root.attributes("-topmost", self.pinned)
        self.ui_state["topmost"] = self.pinned
        save_ui_state(self.ui_state)

    def _toggle_offline(self):
        self.show_offline.set(self.offline_chip.get())
        self._rebuild_devices()

    def _rebuild_devices(self):
        labels = (self._device_labels_all if self.show_offline.get()
                  else self._device_labels_active)
        opts = ["全部设备（不限定）"] + labels
        current = self.device_combo.get()
        if current and current != "全部设备（不限定）" and current not in opts:
            opts.append(current)
        self.device_combo.set_options(opts, keep=current)

    def _on_device(self, _e=None):
        if not self.admin:
            self.banner.configure(
                text="切换作用设备需要管理员权限：点右下角「以管理员重启」。")
        else:
            include = self.read_active()
            if include:
                self.apply(include)
                return
        self._update_status()
        self._update_analysis()
        self._theme_roles = None
        try:
            self._redraw_all_canvases()
        except Exception:
            pass

    def device_pattern(self):
        return self._device_map.get(self.device_combo.get(), "")

    def _on_list_scroll(self, first, last):
        self._list_vsb.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            self._list_vsb.pack_forget()
        else:
            self._list_vsb.pack(side="right", fill="y")

    def _toggle_group(self, gname):
        collapsed = set(self.ui_state.get("collapsed", []))
        if gname in collapsed:
            collapsed.discard(gname)
        else:
            collapsed.add(gname)
        self.ui_state["collapsed"] = sorted(collapsed)
        save_ui_state(self.ui_state)
        self.build()

    def _toggle_volume_match(self):
        self.volume_match = bool(self.volume_toggle.get())
        self.ui_state["volume_match"] = self.volume_match
        save_ui_state(self.ui_state)

    def open_peq(self):
        PeqEditor(self.root, on_saved=self.build, app=self)
        self._theme_roles = None

    def open_opra(self):
        OpraBrowser(self.root, on_import=self.build)

    def add_presets(self):
        files = filedialog.askopenfilenames(
            title="选择 Equalizer APO 预设文件",
            filetypes=[("Equalizer APO 预设", "*.txt"), ("所有文件", "*.*")])
        if not files:
            return
        try:
            os.makedirs(EQ_DIR, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("添加失败", str(exc))
            return
        added = skipped = 0
        for src in files:
            name = os.path.basename(src)
            dst = os.path.join(EQ_DIR, name)
            try:
                if os.path.abspath(src) != os.path.abspath(dst):
                    shutil.copy2(src, dst)
                added += 1
            except Exception:  # noqa: BLE001
                skipped += 1
        self.build()
        messagebox.showinfo(
            "添加预设",
            "已添加 %d 个，跳过 %d 个。\n\n预设目录：\n%s" % (added, skipped, EQ_DIR))

    def _preset_menu(self, fn, event):
        top = tk.Toplevel(self.root)
        top.overrideredirect(True)
        top.configure(bg=BORDER)
        frame = tk.Frame(top, bg=CARD)
        frame.pack(padx=1, pady=1, fill="both", expand=True)

        def choose(action):
            top.destroy()
            action()

        items = (
            ("编辑此预设", lambda: self.edit_preset(fn)),
            ("隐藏此预设", lambda: self._hide_preset(fn)),
            ("删除预设文件（回收站）", lambda: self._delete_preset(fn)),
        )
        for text, action in items:
            lbl = tk.Label(frame, text=text, anchor="w", bg=CARD, fg=TEXT,
                           font=(FONT, 9), padx=14, pady=6, cursor="hand2")
            lbl.pack(fill="x")
            lbl.bind("<Enter>", lambda e, l=lbl: l.configure(bg=ACCENT_SOFT,
                                                             fg=ACCENT))
            lbl.bind("<Leave>", lambda e, l=lbl: l.configure(bg=CARD, fg=TEXT))
            lbl.bind("<Button-1>", lambda e, a=action: choose(a))

        top.update_idletasks()
        w = top.winfo_reqwidth()
        h = top.winfo_reqheight()
        x = min(event.x_root, self.root.winfo_screenwidth() - w - 8)
        y = min(event.y_root, self.root.winfo_screenheight() - h - 8)
        top.attributes("-topmost", True)
        top.geometry("+%d+%d" % (x, y))
        top.update()
        top.lift()
        top.focus_force()
        top.bind("<FocusOut>", lambda e: top.destroy())
        top.bind("<Escape>", lambda e: top.destroy())

    def edit_preset(self, fn):
        path = os.path.join(EQ_DIR, fn)
        if not os.path.isfile(path):
            messagebox.showerror("预设不存在", "找不到预设文件：\n%s" % path)
            return
        try:
            preamp, filters, graphic = parse_preset(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("解析失败", str(exc))
            return
        PeqEditor(self.root, on_saved=self.build, app=self,
                  initial={"preamp": preamp, "filters": filters,
                           "graphic": graphic},
                  target_fn=fn)
        self._theme_roles = None

    def _hide_preset(self, fn):
        hidden = self.ui_state.setdefault("hidden", [])
        if fn not in hidden:
            hidden.append(fn)
            save_ui_state(self.ui_state)
        self.build()

    def _restore_hidden(self):
        self.ui_state["hidden"] = []
        save_ui_state(self.ui_state)
        self.build()

    def _delete_preset(self, fn):
        path = os.path.join(EQ_DIR, fn)
        if not os.path.isfile(path):
            return
        if not messagebox.askyesno(
                "删除预设",
                "把「%s」移到回收站？\n\n文件：%s" % (NAME_MAP.get(fn, fn), path)):
            return
        try:
            _recycle(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("删除失败", str(exc))
            return
        hidden = self.ui_state.setdefault("hidden", [])
        if fn in hidden:
            hidden.remove(fn)
            save_ui_state(self.ui_state)
        if self.read_active() == fn and self.admin:
            self.bypass()
        self.build()

    def _on_wheel(self, event):
        try:
            widget = self.root.winfo_containing(event.x_root, event.y_root)
        except Exception:
            widget = None
        if widget is None:
            return
        parent = widget
        inside = False
        while parent is not None:
            if parent is self.list_canvas:
                inside = True
                break
            parent = getattr(parent, "master", None)
        if inside:
            self.list_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _draw_analysis(self):
        c = self.graph
        if c is None:
            return
        c.delete("all")
        w = c.winfo_width() or 360
        h = c.winfo_height() or 300
        c.create_rectangle(0, 0, w, h, fill=CARD, outline="", tags="abg")
        left, right, top, bottom = 6, 26, 8, 18
        plotw = max(60, w - left - right)
        ploth = max(60, h - top - bottom)
        lo, hi = 20.0, 20000.0

        def x_of(f):
            return left + (math.log10(f) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * plotw

        def y_of(db):
            return top + (40 - db) / 100.0 * ploth

        for db in range(-60, 41, 10):
            yy = y_of(db)
            c.create_line(left, yy, left + plotw, yy, fill=GRID, tags="agrid")
            c.create_text(left + plotw + 3, yy, text=str(db), anchor="w",
                          fill=MUTED, font=(FONT, 7), tags="agrid")
        for f in (20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000):
            xx = x_of(f)
            c.create_line(xx, top, xx, top + ploth, fill=GRID, tags="agrid")
            label = ("%dk" % (f // 1000)) if f >= 1000 else str(f)
            c.create_text(xx, top + ploth + 2, text=label, anchor="n",
                          fill=MUTED, font=(FONT, 7), tags="agrid")
        c.create_line(left, y_of(0), left + plotw, y_of(0), fill=AXIS, tags="aaxis")
        curve = getattr(self, "_curve", None)
        if curve:
            freqs, dbs = curve
            pts = []
            for f, db in zip(freqs, dbs):
                pts.extend([x_of(f), y_of(max(-60, min(40, db)))])
            c.create_line(*pts, fill=ACCENT, width=2, tags="acurve")

    def _update_analysis(self):
        include = self.read_active()
        if include:
            path = os.path.join(EQ_DIR, include)
            if os.path.isfile(path):
                preamp, filters, graphic = parse_preset(path)
            else:
                preamp, filters, graphic = 0.0, [], []
            freqs, dbs = response_curve(preamp, filters, graphic)
            self._curve = (freqs, dbs)
            peak = max(dbs) if dbs else 0.0
            self.stat_peak.configure(text="峰值增益  %+.1f dB" % peak,
                                     fg=RED if peak > 0 else TEXT)
            self.stat_filters.configure(text="滤波器  %d 个" % len(filters))
            self.stat_preamp.configure(text="预增益  %+.1f dB" % preamp)
        else:
            freqs, dbs = response_curve(0.0, [])
            self._curve = (freqs, dbs)
            self.stat_peak.configure(text="峰值增益  —", fg=TEXT)
            self.stat_filters.configure(text="滤波器  —")
            self.stat_preamp.configure(text="预增益  —")
        self._draw_analysis()

    def build(self):
        if getattr(self, "_animating", False):
            self._pending_build = True
            return
        for w in self.frame.winfo_children():
            w.destroy()

        hidden = set(self.ui_state.get("hidden", []))
        presets = [fn for fn in discover() if fn not in hidden]
        active = self.read_active()

        if not self.admin:
            self.banner.configure(
                text="当前为普通模式：只能查看，不能切换。点右下角「以管理员重启」。")
        else:
            self.banner.configure(text="")

        tk.Label(self.frame, text="预设", bg=CARD, fg=MUTED,
                 font=(FONT, 8, "bold")).pack(anchor="w", padx=10, pady=(0, 6))
        if not presets:
            tk.Label(self.frame, text="%s 下没有找到预设文件" % EQ_DIR,
                     bg=CARD, fg=RED, font=(FONT, 10)).pack(anchor="w", padx=4)
        else:
            groups = {}
            for fn in presets:
                groups.setdefault(preset_group(fn), []).append(fn)
            if "collapsed" not in self.ui_state:
                self.ui_state["collapsed"] = sorted(groups)
                save_ui_state(self.ui_state)
            collapsed = set(self.ui_state.get("collapsed", []))
            groups = {}
            for fn in presets:
                groups.setdefault(preset_group(fn), []).append(fn)
            order = [g for g in GROUP_ORDER if g in groups]
            order += [g for g in groups if g not in GROUP_ORDER]
            for gname in order:
                items = groups[gname]
                expanded = gname not in collapsed
                GroupHeader(self.frame, gname, len(items), expanded,
                            lambda gg=gname: self._toggle_group(gg)).pack(
                                fill="x", pady=(6, 0))
                if expanded:
                    for fn in items:
                        label = NAME_MAP.get(fn, fn)
                        PresetRow(self.frame, label, active == fn,
                                  lambda f=fn: self.apply(f), fn=fn,
                                  on_context=self._preset_menu).pack(
                                      fill="x", padx=14, pady=1)
            if hidden:
                tk.Label(self.frame, text="已隐藏 %d 个 · 点此恢复" % len(hidden),
                         bg=CARD, fg=MUTED, font=(FONT, 8),
                         cursor="hand2").pack(anchor="w", padx=12, pady=(8, 2))
                self.frame.winfo_children()[-1].bind(
                    "<Button-1>", lambda e: self._restore_hidden())

        self._update_status()
        self._update_analysis()

    def _update_status(self):
        active = self.read_active()
        dev_label = self.device_combo.get()
        dev_suffix = "" if dev_label.startswith("全部") else "  ·  " + dev_label
        if active:
            self.status.configure(
                text="当前生效：%s%s" % (NAME_MAP.get(active, active), dev_suffix),
                fg=ACCENT)
        else:
            self.status.configure(
                text="当前生效：EQ 已关闭（bypass）" + dev_suffix, fg=MUTED)

    def preview_preset(self, text):
        if not self.admin:
            return False
        try:
            name = "_peq_preview.txt"
            with open(os.path.join(APO_DIR, name), "w", encoding="utf-8") as fh:
                fh.write(text)
            bak = os.path.join(APO_DIR, "config.peq-preview.bak")
            if os.path.exists(CFG) and not os.path.exists(bak):
                shutil.copy2(CFG, bak)
            lines = ["# PEQ 编辑器实时预览 %s" % time.strftime("%H:%M:%S")]
            pattern = self.device_pattern()
            if pattern:
                lines.append("Device: %s" % pattern)
            lines += ["", "Include: %s" % name, ""]
            with open(CFG, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
            return True
        except Exception:
            return False

    def apply(self, fn):
        if not self.admin:
            messagebox.showwarning("需要管理员权限", "请点「以管理员重启」。")
            return
        src = os.path.join(EQ_DIR, fn)
        dst = os.path.join(APO_DIR, fn)
        if not os.path.isfile(src):
            messagebox.showerror("预设不存在", "找不到预设文件：\n%s" % src)
            return
        try:
            if os.path.abspath(src) != os.path.abspath(dst):
                shutil.copy2(src, dst)
            if os.path.exists(CFG):
                bak = os.path.join(
                    APO_DIR, "config.bak-%s.txt" % time.strftime("%Y%m%d-%H%M%S"))
                shutil.copy2(CFG, bak)
            lines = [
                "# 由 EQ 切换器生成 %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
                "# 当前配置: %s" % NAME_MAP.get(fn, fn),
            ]
            pattern = self.device_pattern()
            if pattern:
                lines.append("# 作用设备: %s" % self.device_combo.get())
                lines.append("Device: %s" % pattern)
            lines += ["", "Include: %s" % fn, ""]
            if getattr(self, "volume_match", False):
                try:
                    preamp, filters, graphic = parse_preset(src)
                    comp = estimate_compensation(preamp, filters, graphic)
                    if abs(comp) >= 0.1:
                        lines.append("Preamp: %+.1f dB" % comp)
                        lines.append("# 音量匹配补偿 %+.1f dB" % comp)
                except Exception:
                    pass
            content = "\n".join(lines)
            with open(CFG, "w", encoding="utf-8") as fh:
                fh.write(content)
        except Exception as exc:
            messagebox.showerror("切换失败", str(exc))
            return
        self.build()

    def bypass(self):
        if not self.admin:
            messagebox.showwarning("需要管理员权限", "请点「以管理员重启」。")
            return
        try:
            if os.path.exists(CFG):
                bak = os.path.join(
                    APO_DIR, "config.bak-%s.txt" % time.strftime("%Y%m%d-%H%M%S"))
                shutil.copy2(CFG, bak)
            with open(CFG, "w", encoding="utf-8") as fh:
                fh.write("# EQ 已关闭（由切换器）\n\n")
        except Exception as exc:
            messagebox.showerror("关闭失败", str(exc))
            return
        self.build()


def find_installer():
    for d in (os.path.join(base_dir(), "installer"), base_dir()):
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            low = name.lower()
            if low.startswith("equalizerapo") and low.endswith(".exe"):
                return os.path.join(d, name)
    return None


def _offer_install():
    inst = find_installer()
    if inst:
        ans = messagebox.askyesno(
            "未安装 Equalizer APO",
            "没有检测到 Equalizer APO。\n\n"
            "找到一个安装包：\n%s\n\n是否现在运行安装程序？\n"
            "（安装时勾选你的输出设备，完成后重启）" % inst)
        if ans:
            try:
                os.startfile(inst)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("启动安装失败", str(exc))
    else:
        ans = messagebox.askyesno(
            "未安装 Equalizer APO",
            "没有检测到 Equalizer APO。\n\n"
            "是否打开官方下载页？\n"
            "下载后放进安装程序所在的 installer 文件夹，"
            "重新运行本程序即可自动引导安装。")
        if ans:
            webbrowser.open("https://sourceforge.net/projects/equalizerapo/files/")
    return 1


def main():
    global APO_DIR, CFG
    if not os.path.isdir(APO_DIR):
        picked = filedialog.askopenfilename(
            title="选择 Equalizer APO 的 config.txt（可取消）",
            filetypes=[("config.txt", "config.txt"), ("文本文件", "*.txt")])
        if picked:
            APO_DIR = os.path.dirname(picked)
            CFG = os.path.join(APO_DIR, "config.txt")
            save_apo_dir(APO_DIR)
        else:
            return _offer_install()
    if not os.path.isdir(APO_DIR):
        return _offer_install()

    root = tk.Tk()
    try:
        App(root)
    except Exception as exc:  # noqa: BLE001
        messagebox.showerror("启动失败", "%s\n\n%s" % (type(exc).__name__, exc))
        root.destroy()
        return 1
    if "--selftest" in sys.argv:
        root.update()
        print("selftest ok: presets=%d admin=%s" % (
            len(discover()), is_admin()))
        root.destroy()
        return 0
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    def _hide_preset(self, fn):
        hidden = self.ui_state.setdefault("hidden", [])
        if fn not in hidden:
            hidden.append(fn)
            save_ui_state(self.ui_state)
        self.build()

    def _restore_hidden(self):
        self.ui_state["hidden"] = []
        save_ui_state(self.ui_state)
        self.build()

    def _delete_preset(self, fn):
        path = os.path.join(EQ_DIR, fn)
        if not os.path.isfile(path):
            return
        if not messagebox.askyesno(
                "删除预设",
                "把「%s」移到回收站？\n\n文件：%s" % (NAME_MAP.get(fn, fn), path)):
            return
        try:
            _recycle(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("删除失败", str(exc))
            return
        hidden = self.ui_state.setdefault("hidden", [])
        if fn in hidden:
            hidden.remove(fn)
            save_ui_state(self.ui_state)
        if self.read_active() == fn and self.admin:
            self.bypass()
        self.build()

    def _on_wheel(self, event):
        try:
            widget = self.root.winfo_containing(event.x_root, event.y_root)
        except Exception:
            widget = None
        if widget is None:
            return
        parent = widget
        inside = False
        while parent is not None:
            if parent is self.list_canvas:
                inside = True
                break
            parent = getattr(parent, "master", None)
        if inside:
            self.list_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _draw_analysis(self):
        c = self.graph
        if c is None:
            return
        c.delete("all")
        w = c.winfo_width() or 360
        h = c.winfo_height() or 300
        c.create_rectangle(0, 0, w, h, fill=CARD, outline="", tags="abg")
        left, right, top, bottom = 6, 26, 8, 18
        plotw = max(60, w - left - right)
        ploth = max(60, h - top - bottom)
        lo, hi = 20.0, 20000.0

        def x_of(f):
            return left + (math.log10(f) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * plotw

        def y_of(db):
            return top + (40 - db) / 100.0 * ploth

        for db in range(-60, 41, 10):
            yy = y_of(db)
            c.create_line(left, yy, left + plotw, yy, fill=GRID, tags="agrid")
            c.create_text(left + plotw + 3, yy, text=str(db), anchor="w",
                          fill=MUTED, font=(FONT, 7), tags="agrid")
        for f in (20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000):
            xx = x_of(f)
            c.create_line(xx, top, xx, top + ploth, fill=GRID, tags="agrid")
            label = ("%dk" % (f // 1000)) if f >= 1000 else str(f)
            c.create_text(xx, top + ploth + 2, text=label, anchor="n",
                          fill=MUTED, font=(FONT, 7), tags="agrid")
        c.create_line(left, y_of(0), left + plotw, y_of(0), fill=AXIS, tags="aaxis")
        curve = getattr(self, "_curve", None)
        if curve:
            freqs, dbs = curve
            pts = []
            for f, db in zip(freqs, dbs):
                pts.extend([x_of(f), y_of(max(-60, min(40, db)))])
            c.create_line(*pts, fill=ACCENT, width=2, tags="acurve")

    def _update_analysis(self):
        include = self.read_active()
        if include:
            path = os.path.join(EQ_DIR, include)
            if os.path.isfile(path):
                preamp, filters, graphic = parse_preset(path)
            else:
                preamp, filters, graphic = 0.0, [], []
            freqs, dbs = response_curve(preamp, filters, graphic)
            self._curve = (freqs, dbs)
            peak = max(dbs) if dbs else 0.0
            self.stat_peak.configure(text="峰值增益  %+.1f dB" % peak,
                                     fg=RED if peak > 0 else TEXT)
            self.stat_filters.configure(text="滤波器  %d 个" % len(filters))
            self.stat_preamp.configure(text="预增益  %+.1f dB" % preamp)
        else:
            freqs, dbs = response_curve(0.0, [])
            self._curve = (freqs, dbs)
            self.stat_peak.configure(text="峰值增益  —", fg=TEXT)
            self.stat_filters.configure(text="滤波器  —")
            self.stat_preamp.configure(text="预增益  —")
        self._draw_analysis()

    def build(self):
        if getattr(self, "_animating", False):
            self._pending_build = True
            return
        for w in self.frame.winfo_children():
            w.destroy()

        hidden = set(self.ui_state.get("hidden", []))
        presets = [fn for fn in discover() if fn not in hidden]
        active = self.read_active()

        if not self.admin:
            self.banner.configure(
                text="当前为普通模式：只能查看，不能切换。点右下角「以管理员重启」。")
        else:
            self.banner.configure(text="")

        tk.Label(self.frame, text="预设", bg=CARD, fg=MUTED,
                 font=(FONT, 8, "bold")).pack(anchor="w", padx=10, pady=(0, 6))
        if not presets:
            tk.Label(self.frame, text="%s 下没有找到预设文件" % EQ_DIR,
                     bg=CARD, fg=RED, font=(FONT, 10)).pack(anchor="w", padx=4)
        else:
            groups = {}
            for fn in presets:
                groups.setdefault(preset_group(fn), []).append(fn)
            if "collapsed" not in self.ui_state:
                self.ui_state["collapsed"] = sorted(groups)
                save_ui_state(self.ui_state)
            collapsed = set(self.ui_state.get("collapsed", []))
            groups = {}
            for fn in presets:
                groups.setdefault(preset_group(fn), []).append(fn)
            order = [g for g in GROUP_ORDER if g in groups]
            order += [g for g in groups if g not in GROUP_ORDER]
            for gname in order:
                items = groups[gname]
                expanded = gname not in collapsed
                GroupHeader(self.frame, gname, len(items), expanded,
                            lambda gg=gname: self._toggle_group(gg)).pack(
                                fill="x", pady=(6, 0))
                if expanded:
                    for fn in items:
                        label = NAME_MAP.get(fn, fn)
                        PresetRow(self.frame, label, active == fn,
                                  lambda f=fn: self.apply(f), fn=fn,
                                  on_context=self._preset_menu).pack(
                                      fill="x", padx=14, pady=1)
            if hidden:
                tk.Label(self.frame, text="已隐藏 %d 个 · 点此恢复" % len(hidden),
                         bg=CARD, fg=MUTED, font=(FONT, 8),
                         cursor="hand2").pack(anchor="w", padx=12, pady=(8, 2))
                self.frame.winfo_children()[-1].bind(
                    "<Button-1>", lambda e: self._restore_hidden())

        self._update_status()
        self._update_analysis()

    def _update_status(self):
        active = self.read_active()
        dev_label = self.device_combo.get()
        dev_suffix = "" if dev_label.startswith("全部") else "  ·  " + dev_label
        if active:
            self.status.configure(
                text="当前生效：%s%s" % (NAME_MAP.get(active, active), dev_suffix),
                fg=ACCENT)
        else:
            self.status.configure(
                text="当前生效：EQ 已关闭（bypass）" + dev_suffix, fg=MUTED)

    def preview_preset(self, text):
        if not self.admin:
            return False
        try:
            name = "_peq_preview.txt"
            with open(os.path.join(APO_DIR, name), "w", encoding="utf-8") as fh:
                fh.write(text)
            bak = os.path.join(APO_DIR, "config.peq-preview.bak")
            if os.path.exists(CFG) and not os.path.exists(bak):
                shutil.copy2(CFG, bak)
            lines = ["# PEQ 编辑器实时预览 %s" % time.strftime("%H:%M:%S")]
            pattern = self.device_pattern()
            if pattern:
                lines.append("Device: %s" % pattern)
            lines += ["", "Include: %s" % name, ""]
            with open(CFG, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
            return True
        except Exception:
            return False

    def apply(self, fn):
        if not self.admin:
            messagebox.showwarning("需要管理员权限", "请点「以管理员重启」。")
            return
        src = os.path.join(EQ_DIR, fn)
        dst = os.path.join(APO_DIR, fn)
        if not os.path.isfile(src):
            messagebox.showerror("预设不存在", "找不到预设文件：\n%s" % src)
            return
        try:
            if os.path.abspath(src) != os.path.abspath(dst):
                shutil.copy2(src, dst)
            if os.path.exists(CFG):
                bak = os.path.join(
                    APO_DIR, "config.bak-%s.txt" % time.strftime("%Y%m%d-%H%M%S"))
                shutil.copy2(CFG, bak)
            lines = [
                "# 由 EQ 切换器生成 %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
                "# 当前配置: %s" % NAME_MAP.get(fn, fn),
            ]
            pattern = self.device_pattern()
            if pattern:
                lines.append("# 作用设备: %s" % self.device_combo.get())
                lines.append("Device: %s" % pattern)
            lines += ["", "Include: %s" % fn, ""]
            if getattr(self, "volume_match", False):
                try:
                    preamp, filters, graphic = parse_preset(src)
                    comp = estimate_compensation(preamp, filters, graphic)
                    if abs(comp) >= 0.1:
                        lines.append("Preamp: %+.1f dB" % comp)
                        lines.append("# 音量匹配补偿 %+.1f dB" % comp)
                except Exception:
                    pass
            content = "\n".join(lines)
            with open(CFG, "w", encoding="utf-8") as fh:
                fh.write(content)
        except Exception as exc:
            messagebox.showerror("切换失败", str(exc))
            return
        self.build()

    def bypass(self):
        if not self.admin:
            messagebox.showwarning("需要管理员权限", "请点「以管理员重启」。")
            return
        try:
            if os.path.exists(CFG):
                bak = os.path.join(
                    APO_DIR, "config.bak-%s.txt" % time.strftime("%Y%m%d-%H%M%S"))
                shutil.copy2(CFG, bak)
            with open(CFG, "w", encoding="utf-8") as fh:
                fh.write("# EQ 已关闭（由切换器）\n\n")
        except Exception as exc:
            messagebox.showerror("关闭失败", str(exc))
            return
        self.build()


def find_installer():
    for d in (os.path.join(base_dir(), "installer"), base_dir()):
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            low = name.lower()
            if low.startswith("equalizerapo") and low.endswith(".exe"):
                return os.path.join(d, name)
    return None


def _offer_install():
    inst = find_installer()
    if inst:
        ans = messagebox.askyesno(
            "未安装 Equalizer APO",
            "没有检测到 Equalizer APO。\n\n"
            "找到一个安装包：\n%s\n\n是否现在运行安装程序？\n"
            "（安装时勾选你的输出设备，完成后重启）" % inst)
        if ans:
            try:
                os.startfile(inst)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("启动安装失败", str(exc))
    else:
        ans = messagebox.askyesno(
            "未安装 Equalizer APO",
            "没有检测到 Equalizer APO。\n\n"
            "是否打开官方下载页？\n"
            "下载后放进安装程序所在的 installer 文件夹，"
            "重新运行本程序即可自动引导安装。")
        if ans:
            webbrowser.open("https://sourceforge.net/projects/equalizerapo/files/")
    return 1


def main():
    global APO_DIR, CFG
    if not os.path.isdir(APO_DIR):
        picked = filedialog.askopenfilename(
            title="选择 Equalizer APO 的 config.txt（可取消）",
            filetypes=[("config.txt", "config.txt"), ("文本文件", "*.txt")])
        if picked:
            APO_DIR = os.path.dirname(picked)
            CFG = os.path.join(APO_DIR, "config.txt")
            save_apo_dir(APO_DIR)
        else:
            return _offer_install()
    if not os.path.isdir(APO_DIR):
        return _offer_install()

    root = tk.Tk()
    try:
        App(root)
    except Exception as exc:  # noqa: BLE001
        messagebox.showerror("启动失败", "%s\n\n%s" % (type(exc).__name__, exc))
        root.destroy()
        return 1
    if "--selftest" in sys.argv:
        root.update()
        print("selftest ok: presets=%d admin=%s" % (
            len(discover()), is_admin()))
        root.destroy()
        return 0
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
