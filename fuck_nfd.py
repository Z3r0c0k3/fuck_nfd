import os
import unicodedata
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


def normalize_nfc(name: str) -> str:
    return unicodedata.normalize("NFC", name)


def needs_rename(name: str) -> bool:
    return normalize_nfc(name) != name


def collect_targets(root_paths):
    """Walk inputs and return a list of (old_path, new_path) for items needing rename.

    Order: deepest first, so renaming children before parents keeps paths valid.
    """
    seen = set()
    items = []  # (depth, old_path, new_name)

    def add(path):
        if path in seen:
            return
        seen.add(path)
        depth = path.count(os.sep)
        base = os.path.basename(path.rstrip(os.sep))
        if needs_rename(base):
            items.append((depth, path, normalize_nfc(base)))

    for root in root_paths:
        root = os.path.abspath(root)
        if not os.path.exists(root):
            continue
        add(root)
        if os.path.isdir(root):
            for dirpath, dirnames, filenames in os.walk(root):
                for fn in filenames:
                    add(os.path.join(dirpath, fn))
                for dn in dirnames:
                    add(os.path.join(dirpath, dn))

    items.sort(key=lambda x: x[0], reverse=True)
    return [(p, os.path.join(os.path.dirname(p), new)) for _, p, new in items]


def apply_renames(pairs):
    success, skipped, failed = 0, 0, []
    for old, new in pairs:
        if not os.path.exists(old):
            skipped += 1
            continue
        if os.path.exists(new) and os.path.normcase(old) != os.path.normcase(new):
            failed.append((old, new, "target exists"))
            continue
        try:
            os.rename(old, new)
            success += 1
        except OSError as e:
            failed.append((old, new, str(e)))
    return success, skipped, failed


def parse_drop_paths(data: str):
    """tkinterdnd2 returns a TCL list. Paths with spaces are wrapped in {}."""
    paths, buf, in_brace = [], "", False
    for ch in data:
        if ch == "{":
            in_brace = True
        elif ch == "}":
            in_brace = False
            if buf:
                paths.append(buf)
                buf = ""
        elif ch == " " and not in_brace:
            if buf:
                paths.append(buf)
                buf = ""
        else:
            buf += ch
    if buf:
        paths.append(buf)
    return paths


class App:
    def __init__(self, root):
        self.root = root
        root.title("NFD포맷 파괴광선")
        root.geometry("780x560")

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")

        self.drop_label = tk.Label(
            top,
            text=("여기로 파일 또는 폴더를 드래그하세요"
                  if DND_AVAILABLE else
                  "tkinterdnd2 미설치 — 아래 '폴더 선택' 버튼을 사용하세요"),
            relief="ridge",
            bd=2,
            height=4,
            bg="#f7f7f7",
        )
        self.drop_label.pack(fill="x")

        if DND_AVAILABLE:
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self.on_drop)

        btn_row = ttk.Frame(root, padding=(10, 0))
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="폴더/파일 추가",
                   command=self.add_via_dialog).pack(side="left")
        ttk.Button(btn_row, text="목록 비우기",
                   command=self.clear).pack(side="left", padx=6)

        mid = ttk.LabelFrame(root, text="변환 미리보기 (변경되는 항목만 표시)",
                             padding=8)
        mid.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("old", "new")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings")
        self.tree.heading("old", text="현재 경로 (NFD)")
        self.tree.heading("new", text="변경될 경로 (NFC)")
        self.tree.column("old", width=370, anchor="w")
        self.tree.column("new", width=370, anchor="w")

        ysb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")

        bottom = ttk.Frame(root, padding=10)
        bottom.pack(fill="x")
        self.status = tk.StringVar(value="대기 중")
        ttk.Label(bottom, textvariable=self.status).pack(side="left")
        self.apply_btn = ttk.Button(bottom, text="변환 실행",
                                    command=self.apply, state="disabled")
        self.apply_btn.pack(side="right")

        self.pairs = []

    def on_drop(self, event):
        paths = parse_drop_paths(event.data)
        self.scan(paths)

    def add_via_dialog(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(title="폴더 선택")
        if path:
            self.scan([path])

    def clear(self):
        self.pairs = []
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.status.set("대기 중")
        self.apply_btn.config(state="disabled")

    def scan(self, paths):
        self.clear()
        self.pairs = collect_targets(paths)
        for old, new in self.pairs:
            self.tree.insert("", "end", values=(old, new))
        n = len(self.pairs)
        if n == 0:
            self.status.set("변환할 항목 없음 (모두 NFC 상태)")
            self.apply_btn.config(state="disabled")
        else:
            self.status.set(f"{n}개 항목이 변환 대기 중 — 확인 후 실행하세요")
            self.apply_btn.config(state="normal")

    def apply(self):
        if not self.pairs:
            return
        if not messagebox.askyesno("확인", f"{len(self.pairs)}개 항목을 변환합니다. 진행할까요?"):
            return
        ok, skipped, failed = apply_renames(self.pairs)
        msg = f"성공 {ok}건, 건너뜀 {skipped}건, 실패 {len(failed)}건"
        if failed:
            preview = "\n".join(f"- {os.path.basename(o)}: {err}"
                                for o, _, err in failed[:10])
            messagebox.showwarning("일부 실패", f"{msg}\n\n{preview}")
        else:
            messagebox.showinfo("완료", msg)
        self.clear()


def main():
    root = TkinterDnD.Tk() if DND_AVAILABLE else tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()