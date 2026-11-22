# -*- coding: utf-8 -*-
"""
Equalizer APO 预设实时切换器
- 自动发现 F:\\int\\eq 下的 *.txt 预设
- 点击即切换（写 config.txt，APO 会自动重载）
- 需要管理员权限（写 Program Files）
"""
import ctypes
import os
import shutil
import sys
import time
import tkinter as tk
from tkinter import messagebox

EQ_DIR = r"F:\int\eq"
APO_DIR = r"C:\Program Files\EqualizerAPO\config"
CFG = os.path.join(APO_DIR, "config.txt")

# 显示名映射（没列到的用文件名）
NAME_MAP = {
    "hd490pro-oratory-mix.txt": "490 Pro 实测校准（绒布耳罩）",
    "hd490pro-oratory-prod.txt": "490 Pro 实测校准（厚布耳罩）",
    "hd490pro.txt": "490 Pro 我调 · 补低频+人声",
    "hd490pro-night.txt": "490 Pro 夜间/低音量",
    "hd490pro-thick.txt": "490 Pro 厚声模拟（老功放味）",
    "hd490pro-game.txt": "490 Pro 打瓦 HRTF（通用）",
    "hd490pro-valorant.txt": "490 Pro 打瓦专用（脚步强化）",
    "dt700.txt": "DT 700 Pro X 听歌",
}


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin():
    params = ' '.join('"%s"' % a for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, os.getcwd(), 1)


def discover():
    out = []
    if not os.path.isdir(EQ_DIR):
        return out
    for fn in sorted(os.listdir(EQ_DIR)):
        if fn.lower().endswith(".txt"):
            out.append(fn)
    # 按 NAME_MAP 顺序优先
    order = {k: i for i, k in enumerate(NAME_MAP.keys())}
    out.sort(key=lambda f: (order.get(f, 99), f))
    return out


class App:
    def __init__(self, root):
        self.root = root
        self.admin = is_admin()
        root.title("EQ 切换器")
        root.configure(bg="#141414")
        root.geometry("420x520+140+120")
        root.attributes("-topmost", True)

        tk.Label(root, text="Equalizer APO 配置切换", bg="#141414", fg="#ffffff",
                 font=("Microsoft YaHei", 13)).pack(pady=(14, 2))
        self.dev = tk.Label(root, text="设备：FiiO K11", bg="#141414", fg="#7a7a7a",
                            font=("Microsoft YaHei", 9))
        self.dev.pack()

        self.banner = tk.Label(root, text="", bg="#141414", fg="#ff5252",
                               font=("Microsoft YaHei", 9), wraplength=380)
        self.banner.pack(pady=(6, 0))

        self.frame = tk.Frame(root, bg="#141414")
        self.frame.pack(fill="both", expand=True, padx=16, pady=10)

        self.status = tk.Label(root, text="", bg="#141414", fg="#9e9e9e",
                               font=("Microsoft YaHei", 9), wraplength=380)
        self.status.pack(pady=(0, 4))

        bottom = tk.Frame(root, bg="#141414")
        bottom.pack(fill="x", padx=16, pady=(0, 14))

        tk.Button(bottom, text="刷新列表", command=self.build,
                  bg="#2b2b2b", fg="#dddddd", relief="flat",
                  font=("Microsoft YaHei", 9), padx=10, pady=5).pack(side="left")
        tk.Button(bottom, text="关闭 EQ", command=self.bypass,
                  bg="#3a2b2b", fg="#ff8a80", relief="flat",
                  font=("Microsoft YaHei", 9), padx=10, pady=5).pack(side="left", padx=8)

        if not self.admin:
            tk.Button(bottom, text="以管理员重启", command=relaunch_as_admin,
                      bg="#2b3a2b", fg="#a5d6a7", relief="flat",
                      font=("Microsoft YaHei", 9), padx=10, pady=5).pack(side="right")

        self.buttons = {}
        self.build()

    # ---------- 逻辑 ----------
    def read_active(self):
        try:
            with open(CFG, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    s = line.strip()
                    if s.lower().startswith("include:"):
                        return s.split(":", 1)[1].strip()
        except Exception:
            return None
        return None

    def build(self):
        for w in self.frame.winfo_children():
            w.destroy()
        self.buttons.clear()

        presets = discover()
        active = self.read_active()

        if not self.admin:
            self.banner.configure(text="当前非管理员模式：只能查看，不能切换。\n点右下角按钮以管理员身份重启。")
        else:
            self.banner.configure(text="")

        if not presets:
            tk.Label(self.frame, text="F:\\int\\eq 下没有找到预设文件",
                     bg="#141414", fg="#ff8a80").pack()
            return

        for fn in presets:
            label = NAME_MAP.get(fn, fn)
            is_active = (active == fn)
            bg = "#1f3d2b" if is_active else "#242424"
            fg = "#a5d6a7" if is_active else "#e0e0e0"
            btn = tk.Button(self.frame, text=("● " if is_active else "  ") + label,
                            anchor="w", bg=bg, fg=fg, relief="flat",
                            activebackground="#333333", activeforeground="#ffffff",
                            font=("Microsoft YaHei", 10), padx=12, pady=8,
                            command=lambda f=fn: self.apply(f))
            btn.pack(fill="x", pady=3)
            self.buttons[fn] = btn

        if active:
            self.status.configure(text="当前生效：%s" % NAME_MAP.get(active, active))
        else:
            self.status.configure(text="当前生效：EQ 已关闭")

    def apply(self, fn):
        if not self.admin:
            messagebox.showwarning("需要管理员权限", "请点右下角「以管理员重启」。")
            return
        src = os.path.join(EQ_DIR, fn)
        dst = os.path.join(APO_DIR, fn)
        try:
            if os.path.abspath(src) != os.path.abspath(dst):
                shutil.copy2(src, dst)
            # 备份
            if os.path.exists(CFG):
                bak = os.path.join(APO_DIR, "config.bak-%s.txt" % time.strftime("%Y%m%d-%H%M%S"))
                shutil.copy2(CFG, bak)
            content = "\n".join([
                "# 由 EQ 切换器生成 %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
                "# 当前配置: %s" % NAME_MAP.get(fn, fn),
                "",
                "Include: %s" % fn,
                "",
            ])
            with open(CFG, "w", encoding="utf-8") as fh:
                fh.write(content)
        except Exception as exc:
            messagebox.showerror("切换失败", str(exc))
            return
        self.build()

    def bypass(self):
        if not self.admin:
            messagebox.showwarning("需要管理员权限", "请点右下角「以管理员重启」。")
            return
        try:
            if os.path.exists(CFG):
                bak = os.path.join(APO_DIR, "config.bak-%s.txt" % time.strftime("%Y%m%d-%H%M%S"))
                shutil.copy2(CFG, bak)
            with open(CFG, "w", encoding="utf-8") as fh:
                fh.write("# EQ 已关闭（由切换器）\n\n")
        except Exception as exc:
            messagebox.showerror("关闭失败", str(exc))
            return
        self.build()


def main():
    if not os.path.isdir(APO_DIR):
        ctypes.windll.user32.MessageBoxW(0, "找不到 Equalizer APO 配置目录：\n" + APO_DIR, "EQ 切换器", 0x10)
        return 1
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
