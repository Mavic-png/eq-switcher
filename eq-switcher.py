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
import tkinter as tk
import webbrowser
import winreg
from tkinter import messagebox

def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


EQ_DIR = r"F:\int\eq"
if not os.path.isdir(EQ_DIR):
    EQ_DIR = os.path.join(base_dir(), "presets")
APO_DIR = r"C:\Program Files\EqualizerAPO\config"
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
BG = "#eef1f6"
CARD = "#ffffff"
BORDER = "#e3e8f0"
TEXT = "#16233d"
MUTED = "#7b8496"
ACCENT = "#2f5bea"
ACCENT_SOFT = "#eaf0ff"
GREEN = "#1f9d55"
RED = "#d64545"
HOVER = "#f6f8fc"
ORANGE = "#b45309"
ORANGE_SOFT = "#fff7ed"

FONT = "Microsoft YaHei UI"


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
            fill = ACCENT if not self._hover else "#2448c9"
            text = "#ffffff"
            outline = fill
        elif self.kind == "danger":
            fill = "#fff5f5" if not self._hover else "#ffecec"
            text = RED
            outline = "#f3c7c7"
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
        root.geometry("940x700+120+80")
        root.minsize(860, 600)
        self.ui_state = load_ui_state()
        self.pinned = bool(self.ui_state.get("topmost", True))
        root.attributes("-topmost", self.pinned)

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
        tk.Label(right, text="v1.3", bg=BG, fg=MUTED,
                 font=(FONT, 8)).pack(anchor="e")
        self.mode = tk.Label(right, text="管理员" if self.admin else "普通模式",
                             bg=GREEN if self.admin else ORANGE_SOFT,
                             fg="#ffffff" if self.admin else ORANGE,
                             font=(FONT, 8), padx=8, pady=2)
        self.mode.pack(anchor="e", pady=(4, 0))
        self.pin = PinButton(right, value=self.pinned, command=self._toggle_pin)
        self.pin.pack(anchor="e", pady=(4, 0))

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
        RoundedButton(bottom, "刷新列表", self.build, kind="ghost",
                      width=96).pack(side="left")
        RoundedButton(bottom, "关闭 EQ", self.bypass, kind="danger",
                      width=96).pack(side="left", padx=8)
        if not self.admin:
            RoundedButton(bottom, "以管理员重启", relaunch_as_admin,
                          kind="primary", width=128).pack(side="right")

        self.status = tk.Label(root, text="", bg=BG, fg=MUTED,
                               font=(FONT, 9), anchor="w")
        self.status.pack(fill="x", padx=22, pady=(0, 14))

        self.build()

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

    def _preset_menu(self, fn, event):
        menu = tk.Menu(self.root, tearoff=0, bg=CARD, fg=TEXT,
                       activebackground=ACCENT_SOFT, activeforeground=ACCENT,
                       font=(FONT, 9), bd=0)
        menu.add_command(label="隐藏此预设",
                         command=lambda: self._hide_preset(fn))
        menu.add_command(label="删除预设文件（回收站）",
                         command=lambda: self._delete_preset(fn))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

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
            c.create_line(left, yy, left + plotw, yy, fill="#eef1f6")
            c.create_text(left + plotw + 3, yy, text=str(db), anchor="w",
                          fill=MUTED, font=(FONT, 7))
        for f in (20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000):
            xx = x_of(f)
            c.create_line(xx, top, xx, top + ploth, fill="#eef1f6")
            label = ("%dk" % (f // 1000)) if f >= 1000 else str(f)
            c.create_text(xx, top + ploth + 2, text=label, anchor="n",
                          fill=MUTED, font=(FONT, 7))
        c.create_line(left, y_of(0), left + plotw, y_of(0), fill="#d9dee8")
        curve = getattr(self, "_curve", None)
        if curve:
            freqs, dbs = curve
            pts = []
            for f, db in zip(freqs, dbs):
                pts.extend([x_of(f), y_of(max(-60, min(40, db)))])
            c.create_line(*pts, fill=ACCENT, width=2)

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
            tk.Label(self.frame, text="F:\\int\\eq 下没有找到预设文件",
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

    def apply(self, fn):
        if not self.admin:
            messagebox.showwarning("需要管理员权限", "请点「以管理员重启」。")
            return
        src = os.path.join(EQ_DIR, fn)
        dst = os.path.join(APO_DIR, fn)
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


def main():
    if not os.path.isdir(APO_DIR):
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
