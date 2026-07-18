# SPDX-License-Identifier: AGPL-3.0-only
"""A small Tkinter GUI for psarc2feedpak.

Point it at an UNPACKED Rocksmith arrangement folder, click Convert, get a
.feedpak. Same posture as the CLI: it converts already-unpacked content and
never decrypts or unpacks a raw .psarc — for that, use a tool like DLC Builder
on content you own, then bring the resulting folder here.
"""

from __future__ import annotations

import os
import queue
import shutil
import threading
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog, ttk
from tkinter.scrolledtext import ScrolledText

from psarc2feedpak.audio.normalize import WemConversionError
from psarc2feedpak.convert.pipeline import ConversionError, convert_any

_FEEDBACK_LIBRARY = Path.home() / ".local" / "share" / "feedback" / "library"
_DEFAULT_OUT = Path.home() / "psarc-lab" / "out"


def _autodetect_core() -> str:
    try:
        from psarc2feedpak.convert.pipeline import _locate_core

        return str(_locate_core())
    except Exception:
        return ""


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.q: queue.Queue = queue.Queue()
        root.title("psarc2feedpak")
        root.minsize(620, 470)

        self.in_var = tk.StringVar()
        self.core_var = tk.StringVar(value=_autodetect_core())
        self.out_var = tk.StringVar(value=str(_DEFAULT_OUT))
        self.install_var = tk.BooleanVar(value=True)
        self.legacy_var = tk.BooleanVar(value=False)

        pad = {"padx": 8, "pady": 4}
        frm = ttk.Frame(root, padding=12)
        frm.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        frm.columnconfigure(1, weight=1)

        ttk.Label(frm, text="psarc2feedpak", font=("", 15, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        ttk.Label(
            frm,
            text="Convert an unpacked arrangement — or a whole folder of them — into a feedBack .feedpak.",
            foreground="#666666",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Label(frm, text="Unpacked folder").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.in_var).grid(
            row=2, column=1, sticky="ew", **pad
        )
        ttk.Button(frm, text="Browse…", command=self._choose_input).grid(
            row=2, column=2, **pad
        )

        ttk.Label(frm, text="feedBack core").grid(row=3, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.core_var).grid(
            row=3, column=1, sticky="ew", **pad
        )
        ttk.Button(frm, text="Browse…", command=self._choose_core).grid(
            row=3, column=2, **pad
        )
        self.core_status = ttk.Label(frm, text="")
        self.core_status.grid(row=4, column=1, sticky="w", padx=8)
        self._refresh_core_status()

        ttk.Label(frm, text="Output folder").grid(row=5, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.out_var).grid(
            row=5, column=1, sticky="ew", **pad
        )
        ttk.Button(frm, text="Browse…", command=self._choose_output).grid(
            row=5, column=2, **pad
        )

        opts = ttk.Frame(frm)
        opts.grid(row=6, column=0, columnspan=3, sticky="w", pady=(6, 2))
        ttk.Checkbutton(
            opts,
            text="Install into feedBack library when done",
            variable=self.install_var,
        ).grid(row=0, column=0, sticky="w", padx=8)
        ttk.Checkbutton(
            opts, text="Legacy .sloppak extension", variable=self.legacy_var
        ).grid(row=0, column=1, sticky="w", padx=8)

        self.btn = ttk.Button(frm, text="Convert  →  .feedpak", command=self._start)
        self.btn.grid(row=7, column=0, columnspan=3, sticky="ew", padx=8, pady=(8, 4))

        self.text = ScrolledText(frm, height=12, state="disabled", wrap="word")
        self.text.grid(
            row=8, column=0, columnspan=3, sticky="nsew", padx=8, pady=(4, 4)
        )
        frm.rowconfigure(8, weight=1)

        self.root.after(120, self._drain)
        self._log(
            "Pick an unpacked folder — or a parent folder of many — then hit Convert."
        )

    def _log(self, msg: str) -> None:
        self.q.put(("log", msg))

    def _drain(self) -> None:
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "log":
                    self.text.configure(state="normal")
                    self.text.insert("end", payload + "\n")
                    self.text.see("end")
                    self.text.configure(state="disabled")
                elif kind == "done":
                    self._on_done(payload)
        except queue.Empty:
            pass
        self.root.after(120, self._drain)

    def _refresh_core_status(self) -> None:
        core = self.core_var.get().strip()
        ok = bool(core) and (Path(core) / "lib" / "song.py").exists()
        self.core_status.configure(
            text="✓ found"
            if ok
            else "✗ not found — pick your got-feedback/feedback checkout",
            foreground="#22aa22" if ok else "#cc2222",
        )

    def _choose_input(self) -> None:
        d = filedialog.askdirectory(title="Choose the UNPACKED arrangement folder")
        if d:
            self.in_var.set(d)

    def _choose_core(self) -> None:
        d = filedialog.askdirectory(
            title="Choose the feedBack core (got-feedback/feedback) folder"
        )
        if d:
            self.core_var.set(d)
            self._refresh_core_status()

    def _choose_output(self) -> None:
        d = filedialog.askdirectory(title="Choose the output folder")
        if d:
            self.out_var.set(d)

    def _start(self) -> None:
        src = self.in_var.get().strip()
        if not src:
            self._log("→ Pick an unpacked arrangement folder first.")
            return
        srcp = Path(src)
        if srcp.is_file() and srcp.suffix.lower() == ".psarc":
            self._log(
                "→ That's a still-packed .psarc. Unpack it first with your Rocksmith "
                "toolkit (e.g. DLC Builder) on content you own, then pick the folder it makes."
            )
            return
        core = self.core_var.get().strip()
        if core:
            os.environ["SLOPSMITH_DIR"] = core
        self.btn.configure(state="disabled")
        self._log(f"Converting: {srcp}")
        threading.Thread(target=self._worker, args=(srcp,), daemon=True).start()

    def _worker(self, srcp: Path) -> None:
        try:
            out = Path(self.out_var.get().strip() or _DEFAULT_OUT)
            summary = convert_any(
                srcp,
                out,
                legacy_ext=self.legacy_var.get(),
                on_progress=lambda i, total, name: self._log(
                    f"  [{i + 1}/{total}] {name}"
                ),
            )
            installed = 0
            if self.install_var.get():
                _FEEDBACK_LIBRARY.mkdir(parents=True, exist_ok=True)
                for r in summary["converted"]:
                    pak = Path(r["pak"])
                    shutil.copy2(pak, _FEEDBACK_LIBRARY / pak.name)
                    installed += 1
            summary["installed"] = installed
            self.q.put(("done", {"ok": True, "summary": summary}))
        except (ConversionError, WemConversionError) as e:
            self.q.put(("done", {"ok": False, "error": str(e)}))
        except Exception as e:
            self.q.put(
                ("done", {"ok": False, "error": f"{e}\n{traceback.format_exc()}"})
            )

    def _on_done(self, payload: dict) -> None:
        self.btn.configure(state="normal")
        if not payload["ok"]:
            self._log(f"❌ {payload['error']}")
            return
        s = payload["summary"]
        converted, failed = s["converted"], s["failed"]
        if s["mode"] == "single":
            r = converted[0]
            self._log(
                f"✅ {r['title']} — {r['artist']}  ({r['duration']}s)  →  {Path(r['pak']).name}"
            )
        else:
            for f in failed:
                self._log(f"  ✗ {f['name']}: {f['error']}")
            tail = f", {len(failed)} failed" if failed else ""
            self._log(f"✅ Batch: {len(converted)}/{s['total']} converted{tail}")
        if s.get("installed"):
            self._log(
                f"   Installed {s['installed']} into feedBack — launch it to play."
            )


def main() -> int:
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
