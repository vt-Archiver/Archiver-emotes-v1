import json, threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

import emote_common as ec


class EmoteConsole(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Emote Console — MichiMochievee")
        self.geometry("980x640")

        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        self.left = ttk.Frame(root, padding=8, width=310)
        self.right = ttk.Frame(root)
        self.left.grid(row=0, column=0, sticky="ns")
        self.right.grid(row=0, column=1, sticky="nsew")

        self.btn_refresh = ttk.Button(
            self.left, text="Refresh emotes", command=self._refresh_async
        )
        self.btn_refresh.pack(anchor="w")
        ttk.Separator(self.left, orient="horizontal").pack(fill="x", pady=8)

        self.preview_lbl = ttk.Label(self.left)
        self.preview_lbl.pack()
        self.info_lbl = ttk.Label(self.left, justify="left", wraplength=280)
        self.info_lbl.pack(anchor="w", pady=4)

        top = ttk.Frame(self.right, padding=(6, 4))
        top.pack(fill="x")
        ttk.Label(top, text="Source:").pack(side="left")
        self.src_var = tk.StringVar(value="7tv")
        ttk.Combobox(
            top,
            textvariable=self.src_var,
            state="readonly",
            values=("7tv", "official", "both"),
            width=10,
        ).pack(side="left")
        self.src_var.trace_add("write", lambda *_: self._build_gallery())

        ttk.Label(top, text="   Filter:").pack(side="left")
        self.filter_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.filter_var, width=24).pack(
            side="left", fill="x", expand=True, padx=4
        )
        self.filter_var.trace_add("write", lambda *_: self._build_gallery())

        self.canvas = tk.Canvas(self.right, highlightthickness=0)
        vsb = ttk.Scrollbar(self.right, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(fill="both", expand=True)

        self.grid_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.grid_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

        self.thumb_refs: dict[str, ImageTk.PhotoImage] = {}
        self.metas7 = self._load_meta(ec.DIR_7TV / "metadata.json")
        self.metatw = self._load_meta(ec.DIR_TWITCH / "metadata.json")

        self._build_gallery()
        first = self.metas7 or self.metatw
        if first:
            self._show_details(first[0])

    @staticmethod
    def _load_meta(fp: Path) -> list[dict]:
        try:
            return json.loads(fp.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []

    def _meta_path(self, m: dict) -> Path:
        if "path" in m:
            return Path(m["path"])
        base = ec.DIR_7TV if m.get("source") == "7tv" else ec.DIR_TWITCH
        ext = ".webp" if m.get("source") == "7tv" else ".png"
        return base / f"{m['name']}{ext}"

    def _build_gallery(self) -> None:
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self.thumb_refs.clear()

        source = self.src_var.get()
        metas = (
            self.metas7
            if source == "7tv"
            else self.metatw if source == "official" else self.metas7 + self.metatw
        )

        q = self.filter_var.get().lower().strip()
        if q:
            metas = [
                m
                for m in metas
                if q in m["name"].lower()
                or any(q in t.lower() for t in m.get("tags", []))
            ]

        metas.sort(key=lambda m: m["name"].lower())
        for idx, m in enumerate(metas):
            p = self._meta_path(m)
            if not p.exists():
                continue
            try:
                pil = (
                    Image.open(p)
                    .convert("RGBA")
                    .resize((ec.THUMB_SIZE, ec.THUMB_SIZE), Image.Resampling.LANCZOS)
                )
                img = ImageTk.PhotoImage(pil)
            except Exception:
                continue

            self.thumb_refs[m["name"]] = img
            r, c = divmod(idx, ec.GRID_COLS)
            ttk.Button(
                self.grid_frame,
                image=img,
                style="Toolbutton",
                command=lambda meta=m: self._show_details(meta),
            ).grid(row=r, column=c, padx=4, pady=4)

        self._bind_wheel_recursive(self.grid_frame)

        if metas:
            self._show_details(metas[0])
        else:
            self.preview_lbl.configure(image="")
            self.preview_lbl.image = None
            self.info_lbl.configure(text="(no emotes match)")

    def _show_details(self, m: dict) -> None:
        path = self._meta_path(m)
        if not path.exists():
            return
        try:
            pil = (
                Image.open(path)
                .convert("RGBA")
                .resize((ec.PREVIEW_SIZE, ec.PREVIEW_SIZE), Image.Resampling.LANCZOS)
            )
            img = ImageTk.PhotoImage(pil)
        except Exception:
            return

        self.preview_lbl.configure(image=img)
        self.preview_lbl.image = img
        self.info_lbl.configure(
            text=f"Name: {m['name']}\n"
            f"ID: {m['id']}\n"
            f"Source: {m.get('source','?')}\n"
            f"Owner: {m.get('owner','?')}\n"
            f"Animated: {m.get('animated')}\n"
            f"Downloaded: {m.get('downloaded_at','')}\n"
            f"Tags: {', '.join(m.get('tags', [])) or '(none)'}"
        )

    def _on_wheel(self, e):
        self.canvas.yview_scroll(-1 * (e.delta // 120 or e.delta), "units")

    def _bind_wheel_recursive(self, widget):
        widget.bind("<MouseWheel>", self._on_wheel)
        widget.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        widget.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        for child in widget.winfo_children():
            self._bind_wheel_recursive(child)

    def _refresh_async(self):
        self.btn_refresh.configure(state="disabled")
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self):
        errs = []
        try:
            self.metas7, *_ = ec.fetch_7tv_emotes()
        except Exception as ex:
            errs.append(f"7TV: {ex}")
        try:
            self.metatw, *_ = ec.fetch_twitch_emotes()
        except Exception as ex:
            errs.append(f"Twitch: {ex}")
        self.after(0, lambda: self._refresh_done(errs))

    def _refresh_done(self, errs: list[str]):
        self._build_gallery()
        self.btn_refresh.configure(state="normal")
        if errs:
            messagebox.showwarning("Refresh completed with errors", "\n".join(errs))


if __name__ == "__main__":
    EmoteConsole().mainloop()
