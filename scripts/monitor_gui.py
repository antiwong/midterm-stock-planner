#!/usr/bin/env python3
"""
Regression Test Monitor — GUI
==============================
Small floating window that shows live regression test progress.

Usage:
    python scripts/monitor_gui.py
"""

import sqlite3
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk

DB_PATH = Path(__file__).parent.parent / "data" / "runs.db"
REFRESH_MS = 5000


def get_process_info():
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        procs = []
        for line in result.stdout.split("\n"):
            if "run_regression" in line and "grep" not in line and "monitor" not in line:
                parts = line.split()
                if len(parts) >= 11:
                    procs.append({"pid": parts[1], "cpu": parts[2], "mem": parts[3], "time": parts[9]})
        return procs
    except Exception:
        return []


def query_db():
    if not DB_PATH.exists():
        return [], {}
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    tests = conn.execute(
        "SELECT * FROM regression_tests ORDER BY created_at DESC LIMIT 8"
    ).fetchall()
    steps_by_test = {}
    for t in tests:
        rid = t["regression_id"]
        rows = conn.execute(
            "SELECT * FROM regression_steps WHERE regression_id = ? ORDER BY step_number",
            (rid,),
        ).fetchall()
        steps_by_test[rid] = rows
    conn.close()
    return tests, steps_by_test


def fmt_duration(seconds):
    if seconds is None:
        return "—"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


class MonitorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("QuantaAlpha Monitor")
        self.root.configure(bg="#1a1a2e")
        self.root.attributes("-topmost", True)
        self.root.geometry("620x480")
        self.root.minsize(500, 300)

        # Header
        header = tk.Frame(self.root, bg="#16213e", pady=6)
        header.pack(fill="x")
        tk.Label(
            header, text="QuantaAlpha Regression Monitor",
            font=("SF Mono", 13, "bold"), fg="#e0e0e0", bg="#16213e"
        ).pack(side="left", padx=10)
        self.time_label = tk.Label(
            header, text="", font=("SF Mono", 10), fg="#888", bg="#16213e"
        )
        self.time_label.pack(side="right", padx=10)

        # Process bar
        self.proc_frame = tk.Frame(self.root, bg="#1a1a2e", pady=2)
        self.proc_frame.pack(fill="x", padx=10)
        self.proc_label = tk.Label(
            self.proc_frame, text="", font=("SF Mono", 10),
            fg="#888", bg="#1a1a2e", anchor="w"
        )
        self.proc_label.pack(fill="x")

        # Scrollable content
        container = tk.Frame(self.root, bg="#1a1a2e")
        container.pack(fill="both", expand=True, padx=5, pady=5)

        canvas = tk.Canvas(container, bg="#1a1a2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.content = tk.Frame(canvas, bg="#1a1a2e")

        self.content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel scrolling
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        self.refresh()
        self.root.mainloop()

    def refresh(self):
        tests, steps_by_test = query_db()
        procs = get_process_info()
        now = datetime.now().strftime("%H:%M:%S")
        self.time_label.config(text=now)

        # Process info
        if procs:
            parts = []
            for p in procs:
                parts.append(f"PID {p['pid']}  CPU {p['cpu']}%  MEM {p['mem']}%  TIME {p['time']}")
            self.proc_label.config(text="  ".join(parts), fg="#4ade80")
        else:
            self.proc_label.config(text="No regression processes running", fg="#666")

        # Clear content
        for w in self.content.winfo_children():
            w.destroy()

        for t in tests:
            rid = t["regression_id"]
            status = t["status"]
            name = t["name"] or rid[:20]
            total = t["total_steps"] or 0
            steps = steps_by_test.get(rid, [])
            done = len(steps)

            colors = {"running": "#38bdf8", "completed": "#4ade80", "failed": "#f87171"}
            color = colors.get(status, "#888")
            icons = {"running": "⟳", "completed": "✓", "failed": "✗"}
            icon = icons.get(status, "?")

            # Test card
            card = tk.Frame(self.content, bg="#0f3460", relief="flat", pady=4, padx=8)
            card.pack(fill="x", pady=2, padx=4)

            # Title row
            title_row = tk.Frame(card, bg="#0f3460")
            title_row.pack(fill="x")

            tk.Label(
                title_row, text=f"{icon} {name}",
                font=("SF Mono", 11, "bold"), fg=color, bg="#0f3460", anchor="w"
            ).pack(side="left")

            dur = fmt_duration(t["duration_seconds"])
            tk.Label(
                title_row, text=f"{status}  {done}/{total} steps  {dur}",
                font=("SF Mono", 9), fg="#888", bg="#0f3460", anchor="e"
            ).pack(side="right")

            # Progress bar for running
            if status == "running" and total > 0:
                prog = tk.Frame(card, bg="#0f3460", pady=2)
                prog.pack(fill="x")
                bar_bg = tk.Frame(prog, bg="#1a1a2e", height=6)
                bar_bg.pack(fill="x")
                pct = done / total if total else 0
                bar_fill = tk.Frame(bar_bg, bg="#38bdf8", height=6, width=max(1, int(pct * 580)))
                bar_fill.place(x=0, y=0)

            # Step table
            if steps:
                table = tk.Frame(card, bg="#0a1929")
                table.pack(fill="x", pady=(4, 0))

                # Header
                hdr = tk.Frame(table, bg="#0a1929")
                hdr.pack(fill="x")
                for col, w in [("Step", 4), ("Feature", 18), ("Sharpe", 9), ("RankIC", 9), ("MargIC", 9)]:
                    tk.Label(
                        hdr, text=col, font=("SF Mono", 9, "bold"),
                        fg="#666", bg="#0a1929", width=w, anchor="w"
                    ).pack(side="left")

                for s in steps:
                    row = tk.Frame(table, bg="#0a1929")
                    row.pack(fill="x")

                    sh = f"{s['sharpe_ratio']:+.3f}" if s['sharpe_ratio'] is not None else "—"
                    ric = f"{s['mean_rank_ic']:.4f}" if s['mean_rank_ic'] is not None else "—"
                    mic_val = s['marginal_rank_ic']
                    mic = f"{mic_val:+.4f}" if mic_val is not None else "—"

                    mic_color = "#e0e0e0"
                    if mic_val is not None:
                        if mic_val > 0.005:
                            mic_color = "#4ade80"
                        elif mic_val < -0.005:
                            mic_color = "#f87171"

                    for text, w, fg in [
                        (str(s['step_number']), 4, "#e0e0e0"),
                        (s['feature_added'], 18, "#e0e0e0"),
                        (sh, 9, "#e0e0e0"),
                        (ric, 9, "#e0e0e0"),
                        (mic, 9, mic_color),
                    ]:
                        tk.Label(
                            row, text=text, font=("SF Mono", 9),
                            fg=fg, bg="#0a1929", width=w, anchor="w"
                        ).pack(side="left")

        # Schedule next refresh
        self.root.after(REFRESH_MS, self.refresh)


if __name__ == "__main__":
    MonitorApp()
