# ui_toolbar.py
import tkinter as tk
from tkinter import filedialog, messagebox

class UIToolbar:
    def __init__(self, app):
        self.app = app

    def build_toolbar(self, root):
        # ===== ツールバー全体 =====
        tb = tk.Frame(root, bg="#f0f0f0", padx=6, pady=4)
        tb.pack(side=tk.TOP, fill=tk.X)

        # ==== ファイル操作 ====
        file_frame = tk.Frame(tb, bg="#f0f0f0")
        file_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(file_frame, text="📄 File:", bg="#f0f0f0").pack(side=tk.LEFT)
        tk.Button(file_frame, text="Open", command=self.app.open_pdf_dialog).pack(side=tk.LEFT, padx=2)
        tk.Button(file_frame, text="Save JSON", command=self.app.save_project_dialog).pack(side=tk.LEFT, padx=2)
        tk.Button(file_frame, text="Load JSON", command=self.app.load_project_dialog).pack(side=tk.LEFT, padx=2)
        tk.Button(file_frame, text="Export PDF", command=self.app.export_pdf_dialog).pack(side=tk.LEFT, padx=2)

        # ==== ページ操作 ====
        nav_frame = tk.Frame(tb, bg="#f0f0f0")
        nav_frame.pack(side=tk.LEFT, padx=15)
        tk.Label(nav_frame, text="📘 Page:", bg="#f0f0f0").pack(side=tk.LEFT)
        tk.Button(nav_frame, text="◀ Prev", command=self.app.prev_page).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="Next ▶", command=self.app.next_page).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="✂️ shape_del", fg="red", command=self.app.delete_selected).pack(side=tk.LEFT, padx=2)

        # ==== モード切り替え ====
        mode_frame = tk.Frame(tb, bg="#f0f0f0")
        mode_frame.pack(side=tk.LEFT, padx=15)
        tk.Label(mode_frame, text="🛠 Mode:", bg="#f0f0f0").pack(side=tk.LEFT)
        self.app.btn_move = tk.Button(mode_frame, text="Move", command=lambda: self.app.toggle_mode(self.app.btn_move, "move"))
        self.app.btn_draw = tk.Button(mode_frame, text="Draw", command=lambda: self.app.toggle_mode(self.app.btn_draw, "draw"))
        self.app.btn_move.pack(side=tk.LEFT, padx=2)
        self.app.btn_draw.pack(side=tk.LEFT, padx=2)

        # ==== 図形ボタン ====
        shape_frame = tk.Frame(tb, bg="#f0f0f0")
        shape_frame.pack(side=tk.LEFT, padx=15)
        tk.Label(shape_frame, text="✏️ Shape:", bg="#f0f0f0").pack(side=tk.LEFT)
        self.app.shape_buttons = {}
        for text, name in [
            ("⬛ Rect", "rect"),
            ("🟣 Ellipse", "ellipse"),
            ("➖ Line", "line"),
            ("🔺 Triangle", "triangle"),
            ("📝 Text", "text"),
        ]:
            b = tk.Button(shape_frame, text=text, command=lambda s=name: self.app.toggle_shape(s))
            b.pack(side=tk.LEFT, padx=1)
            self.app.shape_buttons[name] = b

        # ==== 拡大縮小 ====
        zoom_frame = tk.Frame(tb, bg="#f0f0f0")
        zoom_frame.pack(side=tk.RIGHT, padx=10)
        tk.Label(zoom_frame, text="🔍 Zoom:", bg="#f0f0f0").pack(side=tk.LEFT)
        tk.Button(zoom_frame, text="+", command=self.app.zoom_in, width=3).pack(side=tk.LEFT, padx=2)
        tk.Button(zoom_frame, text="-", command=self.app.zoom_out, width=3).pack(side=tk.LEFT, padx=2)

        # ==== ステータスバー ====
        self.app.status = tk.Label(root, text="No PDF loaded", anchor="w", bg="#eaeaea", relief="sunken")
        self.app.status.pack(side=tk.BOTTOM, fill=tk.X)
