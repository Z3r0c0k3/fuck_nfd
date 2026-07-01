import os
import unicodedata
from dataclasses import dataclass
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False


@dataclass(frozen=True)
class FileOperation:
    kind: str
    label: str
    old_path: str
    new_path: str


def normalize_nfc(name: str) -> str:
    return unicodedata.normalize("NFC", name)


def needs_rename(name: str) -> bool:
    return normalize_nfc(name) != name


def path_key(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def same_path(left: str, right: str) -> bool:
    return path_key(left) == path_key(right)


def make_unique_destination(directory: str, filename: str, reserved) -> str:
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(directory, filename)
    index = 1

    while os.path.exists(candidate) or path_key(candidate) in reserved:
        candidate = os.path.join(directory, f"{base} ({index}){ext}")
        index += 1

    reserved.add(path_key(candidate))
    return candidate


def collect_rename_targets(root_paths, excluded_paths=None):
    """Walk inputs and return rename operations for items needing NFC conversion.

    Order: deepest first, so renaming children before parents keeps paths valid.
    """
    excluded_paths = excluded_paths or set()
    seen = set()
    items = []  # (depth, old_path, new_name)

    def add(path):
        key = path_key(path)
        if key in seen or key in excluded_paths:
            return
        seen.add(key)
        depth = os.path.abspath(path).count(os.sep)
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
    return [
        FileOperation("rename", "NFD 변환", old, os.path.join(os.path.dirname(old), new))
        for _, old, new in items
    ]


def collect_gather_targets(root_paths, normalize_names=False):
    """Return move operations that gather files from child folders into each root."""
    operations = []
    moved_paths = set()
    seen_roots = set()

    for root in root_paths:
        root = os.path.abspath(root)
        root_key = path_key(root)
        if root_key in seen_roots or not os.path.isdir(root):
            continue
        seen_roots.add(root_key)

        reserved = set()
        for entry in os.scandir(root):
            if entry.is_file():
                final_name = normalize_nfc(entry.name) if normalize_names else entry.name
                reserved.add(path_key(os.path.join(root, final_name)))

        for dirpath, _, filenames in os.walk(root):
            if same_path(dirpath, root):
                continue

            for filename in filenames:
                old_path = os.path.join(dirpath, filename)
                final_name = normalize_nfc(filename) if normalize_names else filename
                new_path = make_unique_destination(root, final_name, reserved)

                if same_path(old_path, new_path):
                    continue

                moved_paths.add(path_key(old_path))
                operations.append(
                    FileOperation("gather", "파일 모으기", old_path, new_path)
                )

    return operations, moved_paths


def collect_operations(root_paths, normalize_enabled=True, gather_enabled=False):
    operations = []
    moved_paths = set()

    if gather_enabled:
        gather_operations, moved_paths = collect_gather_targets(
            root_paths, normalize_names=normalize_enabled
        )
        operations.extend(gather_operations)

    if normalize_enabled:
        operations.extend(collect_rename_targets(root_paths, excluded_paths=moved_paths))

    return operations


def apply_operations(operations):
    success, skipped, failed = 0, 0, []

    for operation in operations:
        old, new = operation.old_path, operation.new_path
        if not os.path.exists(old):
            skipped += 1
            continue
        if same_path(old, new):
            skipped += 1
            continue
        if os.path.exists(new):
            failed.append((operation, "target exists"))
            continue

        try:
            os.makedirs(os.path.dirname(new), exist_ok=True)
            os.rename(old, new)
            success += 1
        except OSError as error:
            failed.append((operation, str(error)))

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
        root.title("씨@발 NFD 처단기")
        root.geometry("880x620")

        self.root_paths = []
        self.operations = []
        self.normalize_enabled = tk.BooleanVar(value=True)
        self.gather_enabled = tk.BooleanVar(value=False)

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")

        self.drop_label = tk.Label(
            top,
            text=(
                "여기로 파일 또는 폴더를 드래그하세요"
                if DND_AVAILABLE
                else "tkinterdnd2 미설치 - 아래 '폴더 선택' 버튼을 사용하세요"
            ),
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
        ttk.Button(btn_row, text="폴더 추가", command=self.add_via_dialog).pack(
            side="left"
        )
        ttk.Button(btn_row, text="목록 비우기", command=self.clear).pack(
            side="left", padx=6
        )

        option_frame = ttk.LabelFrame(root, text="작업 옵션", padding=8)
        option_frame.pack(fill="x", padx=10, pady=(10, 0))
        ttk.Checkbutton(
            option_frame,
            text="NFD 파일명을 NFC로 변환",
            variable=self.normalize_enabled,
            command=self.refresh_preview,
        ).pack(side="left")
        ttk.Checkbutton(
            option_frame,
            text="하위 폴더의 흩어진 파일을 선택 폴더로 모으기",
            variable=self.gather_enabled,
            command=self.refresh_preview,
        ).pack(side="left", padx=18)

        mid = ttk.LabelFrame(root, text="작업 미리보기", padding=8)
        mid.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("kind", "old", "new")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings")
        self.tree.heading("kind", text="작업")
        self.tree.heading("old", text="현재 경로")
        self.tree.heading("new", text="변경될 경로")
        self.tree.column("kind", width=110, anchor="center", stretch=False)
        self.tree.column("old", width=350, anchor="w")
        self.tree.column("new", width=350, anchor="w")

        ysb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")

        bottom = ttk.Frame(root, padding=10)
        bottom.pack(fill="x")
        self.status = tk.StringVar(value="대기 중")
        ttk.Label(bottom, textvariable=self.status).pack(side="left")
        self.apply_btn = ttk.Button(
            bottom, text="선택 작업 실행", command=self.apply, state="disabled"
        )
        self.apply_btn.pack(side="right")

    def on_drop(self, event):
        self.add_paths(parse_drop_paths(event.data))

    def add_via_dialog(self):
        path = filedialog.askdirectory(title="폴더 선택")
        if path:
            self.add_paths([path])

    def add_paths(self, paths):
        known = {path_key(path) for path in self.root_paths}
        for path in paths:
            absolute = os.path.abspath(path)
            key = path_key(absolute)
            if os.path.exists(absolute) and key not in known:
                self.root_paths.append(absolute)
                known.add(key)
        self.refresh_preview()

    def clear_preview(self):
        self.operations = []
        for item in self.tree.get_children():
            self.tree.delete(item)

    def clear(self):
        self.root_paths = []
        self.clear_preview()
        self.status.set("대기 중")
        self.apply_btn.config(state="disabled")

    def selected_option_labels(self):
        labels = []
        if self.normalize_enabled.get():
            labels.append("NFD 변환")
        if self.gather_enabled.get():
            labels.append("파일 모으기")
        return labels

    def refresh_preview(self):
        self.clear_preview()

        if not self.root_paths:
            self.status.set("대기 중")
            self.apply_btn.config(state="disabled")
            return

        selected_options = self.selected_option_labels()
        if not selected_options:
            self.status.set("실행할 작업 옵션을 선택하세요")
            self.apply_btn.config(state="disabled")
            return

        self.operations = collect_operations(
            self.root_paths,
            normalize_enabled=self.normalize_enabled.get(),
            gather_enabled=self.gather_enabled.get(),
        )

        for operation in self.operations:
            self.tree.insert(
                "",
                "end",
                values=(operation.label, operation.old_path, operation.new_path),
            )

        count = len(self.operations)
        if count == 0:
            self.status.set("실행할 항목 없음")
            self.apply_btn.config(state="disabled")
        else:
            options = ", ".join(selected_options)
            self.status.set(f"{count}개 작업 대기 중 ({options}) - 확인 후 실행하세요")
            self.apply_btn.config(state="normal")

    def apply(self):
        if not self.operations:
            return

        if not messagebox.askyesno(
            "확인", f"{len(self.operations)}개 작업을 실행합니다. 진행할까요?"
        ):
            return

        ok, skipped, failed = apply_operations(self.operations)
        msg = f"성공 {ok}건, 건너뜀 {skipped}건, 실패 {len(failed)}건"

        if failed:
            preview = "\n".join(
                f"- [{operation.label}] {os.path.basename(operation.old_path)}: {error}"
                for operation, error in failed[:10]
            )
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
