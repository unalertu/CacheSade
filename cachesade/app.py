from __future__ import annotations

import json
import os
import threading
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import messagebox, ttk

from cachesade.core import CleanResult, ScanResult, clean_result, human_size, scan_all


APP_NAME = "CacheSade"
CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
CONFIG_FILE = CONFIG_DIR / "settings.json"


class CacheSadeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CacheSade")
        self.geometry("980x620")
        self.minsize(820, 520)
        self.results: dict[str, ScanResult] = {}
        self.selected: set[str] = set()
        self.settings = self._load_settings()
        self.reminder_due = self._is_reminder_due(self.settings.get("last_scan"))
        self._build_ui()
        self.after(250, self.start_scan)
        self.after(700, self._show_due_reminder)

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")

        header = ttk.Frame(self, padding=(18, 16, 18, 8))
        header.pack(fill="x")
        ttk.Label(header, text="CacheSade", font=("Segoe UI", 20, "bold")).pack(side="left")
        ttk.Label(
            header,
            text="Yalnız bilinen, yeniden oluşturulabilir önbellekler",
            foreground="#555555",
        ).pack(side="left", padx=(14, 0), pady=(7, 0))

        toolbar = ttk.Frame(self, padding=(18, 4, 18, 10))
        toolbar.pack(fill="x")
        self.scan_button = ttk.Button(toolbar, text="Yeniden Tara", command=self.start_scan)
        self.scan_button.pack(side="left")
        self.clean_button = ttk.Button(toolbar, text="Seçilenleri Temizle", command=self.confirm_clean)
        self.clean_button.pack(side="left", padx=8)
        self.reminder_var = tk.BooleanVar(value=bool(self.settings.get("monthly_reminder", True)))
        ttk.Checkbutton(
            toolbar,
            text="30 günde bir tarama hatırlat",
            variable=self.reminder_var,
            command=self._save_settings,
        ).pack(side="right")

        columns = ("selected", "name", "category", "size", "files", "paths")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        headings = {
            "selected": "Seç",
            "name": "Önbellek",
            "category": "Kategori",
            "size": "Boyut",
            "files": "Dosya",
            "paths": "Yol",
        }
        widths = {"selected": 50, "name": 220, "category": 110, "size": 85, "files": 65, "paths": 390}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], minwidth=45, anchor="w")
        self.tree.column("selected", anchor="center", stretch=False)
        self.tree.column("size", anchor="e", stretch=False)
        self.tree.column("files", anchor="e", stretch=False)
        self.tree.bind("<Button-1>", self._tree_click)
        self.tree.bind("<<TreeviewSelect>>", self._show_description)
        self.tree.pack(fill="both", expand=True, padx=18)

        info = ttk.Frame(self, padding=(18, 8))
        info.pack(fill="x")
        self.description = ttk.Label(info, text="Satıra tıklayarak ayrıntıyı görün.", foreground="#444444")
        self.description.pack(anchor="w")

        bottom = ttk.Frame(self, padding=(18, 4, 18, 16))
        bottom.pack(fill="x")
        self.progress = ttk.Progressbar(bottom, mode="indeterminate", length=180)
        self.progress.pack(side="left")
        self.status = ttk.Label(bottom, text="Hazır")
        self.status.pack(side="left", padx=10)
        ttk.Label(
            bottom,
            text="Kilitli dosyalar atlanır • Tarayıcı verilerine dokunulmaz",
            foreground="#666666",
        ).pack(side="right")

    def _set_busy(self, busy: bool, text: str) -> None:
        state = "disabled" if busy else "normal"
        self.scan_button.configure(state=state)
        self.clean_button.configure(state=state)
        self.status.configure(text=text)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def start_scan(self) -> None:
        self._set_busy(True, "Taranıyor…")
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self) -> None:
        results = scan_all()
        self.after(0, lambda: self._finish_scan(results))

    def _finish_scan(self, results: list[ScanResult]) -> None:
        self.results = {result.rule.key: result for result in results}
        self.selected.intersection_update(self.results)
        for item in self.tree.get_children():
            self.tree.delete(item)
        total = 0
        found = 0
        for result in results:
            if not result.paths:
                continue
            total += result.size_bytes
            found += 1
            self.tree.insert(
                "", "end", iid=result.rule.key,
                values=(
                    "☑" if result.rule.key in self.selected else "☐",
                    result.rule.name,
                    result.rule.category,
                    human_size(result.size_bytes),
                    result.file_count,
                    " ; ".join(str(path) for path in result.paths),
                ),
            )
        self.settings["last_scan"] = datetime.now().isoformat(timespec="seconds")
        self._save_settings()
        self._set_busy(False, f"{found} kategori bulundu • Temizlenebilir: {human_size(total)}")

    def _tree_click(self, event: tk.Event) -> None:
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if item and column == "#1":
            if item in self.selected:
                self.selected.remove(item)
            else:
                self.selected.add(item)
            values = list(self.tree.item(item, "values"))
            values[0] = "☑" if item in self.selected else "☐"
            self.tree.item(item, values=values)

    def _show_description(self, _event: object = None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        result = self.results.get(selection[0])
        if result:
            suffix = " İlk çalıştırmada kısa süreli shader derleme/takılma olabilir." if result.rule.category == "Ekran kartı" else ""
            self.description.configure(text=result.rule.description + suffix)

    def confirm_clean(self) -> None:
        choices = [self.results[key] for key in self.selected if key in self.results and self.results[key].file_count]
        if not choices:
            messagebox.showinfo(APP_NAME, "Temizlemek için en az bir dolu kategori seçin.")
            return
        total = sum(item.size_bytes for item in choices)
        names = "\n".join(f"• {item.rule.name}: {human_size(item.size_bytes)}" for item in choices)
        question = (
            f"Seçilen dosyalar kalıcı olarak silinecek:\n\n{names}\n\n"
            f"Toplam: {human_size(total)}\n\n"
            "İlgili oyun ve uygulamaları kapatmanız önerilir. Devam edilsin mi?"
        )
        if not messagebox.askyesno("Temizlemeyi onayla", question, icon="warning"):
            return
        self._set_busy(True, "Temizleniyor…")
        threading.Thread(target=self._clean_worker, args=(choices,), daemon=True).start()

    def _clean_worker(self, choices: list[ScanResult]) -> None:
        outcomes = [clean_result(item) for item in choices]
        self.after(0, lambda: self._finish_clean(outcomes))

    def _finish_clean(self, outcomes: list[CleanResult]) -> None:
        deleted = sum(item.deleted_bytes for item in outcomes)
        files = sum(item.deleted_files for item in outcomes)
        skipped = [entry for item in outcomes for entry in item.skipped]
        detail = f"{files} dosya silindi, {human_size(deleted)} alan açıldı."
        if skipped:
            detail += f"\n\n{len(skipped)} kilitli veya erişilemeyen dosya atlandı."
        messagebox.showinfo("Temizlik tamamlandı", detail)
        self.selected.clear()
        self.start_scan()

    def _load_settings(self) -> dict:
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"monthly_reminder": True}

    def _save_settings(self) -> None:
        self.settings["monthly_reminder"] = bool(self.reminder_var.get()) if hasattr(self, "reminder_var") else True
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _show_due_reminder(self) -> None:
        if self.reminder_var.get() and self.reminder_due:
            messagebox.showinfo(APP_NAME, "Son taramanın üzerinden 30 gün geçti. Yeni tarama otomatik başlatıldı.")

    @staticmethod
    def _is_reminder_due(value: object) -> bool:
        try:
            return datetime.fromisoformat(str(value)) + timedelta(days=30) <= datetime.now()
        except (TypeError, ValueError):
            return False


def main() -> None:
    CacheSadeApp().mainloop()


if __name__ == "__main__":
    main()

