# ui_toolbar.py
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox, colorchooser

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
        tk.Button(file_frame, text="PDF", command=self.app.export_pdf_dialog).pack(side=tk.LEFT, padx=2)
        tk.Button(file_frame, text="集計", command=self.app.run_total_and_page_summary).pack(side=tk.LEFT, padx=2)
        tk.Button(
            file_frame,
            text="全ページ集計",
            command=self.app.run_total_and_all_page_summary
        ).pack(side=tk.LEFT, padx=2)

        # ==== ページ操作 ====
        nav_frame = tk.Frame(tb, bg="#f0f0f0")
        nav_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(nav_frame, text="📘 Page:", bg="#f0f0f0").pack(side=tk.LEFT)
        tk.Button(nav_frame, text="◀ Prev", command=self.app.prev_page).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="Next ▶", command=self.app.next_page).pack(side=tk.LEFT, padx=2)

        # ==== モード切り替え ====
        mode_frame = tk.Frame(tb, bg="#f0f0f0")
        mode_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(mode_frame, text="🛠 Mode:", bg="#f0f0f0").pack(side=tk.LEFT)
        self.app.btn_move = tk.Button(mode_frame, text="Move", command=lambda: self.app.toggle_mode(self.app.btn_move, "move"))
        self.app.btn_draw = tk.Button(mode_frame, text="Draw", command=lambda: self.app.toggle_mode(self.app.btn_draw, "draw"))
        self.app.btn_move.pack(side=tk.LEFT, padx=2)
        self.app.btn_draw.pack(side=tk.LEFT, padx=2)

        # ==== 図形ボタン ====
        shape_frame = tk.Frame(tb, bg="#f0f0f0")
        shape_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(shape_frame, text="Shape:", bg="#f0f0f0").pack(side=tk.LEFT)
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

        # ==== 固定色パレット ====
        color_frame = tk.Frame(tb, bg="#f0f0f0")
        color_frame.pack(side=tk.LEFT, padx=15)
        tk.Label(color_frame, text="🎨 Color:", bg="#f0f0f0").pack(side=tk.LEFT)

        # 現在の色を保持
        self.app.current_color = "#000000"

        # 固定色マッピング
        fixed_colors = [
            ("壁", "#ff0000"),
            ("屋根", "#0000ff"),
            ("B下", "#00aa00"),
            ("下屋", "#ffa500"),
            ("窓", "#800080"),
            ("ドア", "#999999"),
        ]

        def make_color_button(frame, name, color):
            return tk.Button(
                frame,
                text=name,
                bg=color,
                fg="white" if color not in ("#ffff00", "#ffffff") else "black",
                width=4,
                relief="raised",
                command=lambda c=color: self.set_color(c),
            )

        for name, c in fixed_colors:
            make_color_button(color_frame, name, c).pack(side=tk.LEFT, padx=1)

        # カスタム選択ボタン
        tk.Button(color_frame, text="Custom", command=self.choose_color).pack(side=tk.LEFT, padx=4)

        # 現在色プレビュー
        self.app.color_preview = tk.Label(color_frame, width=3, bg=self.app.current_color, relief="solid", borderwidth=1)
        self.app.color_preview.pack(side=tk.LEFT, padx=4)

        # ==== 拡大縮小 ====
        zoom_frame = tk.Frame(tb, bg="#f0f0f0")
        zoom_frame.pack(side=tk.RIGHT, padx=5)
        tk.Label(zoom_frame, text="🔍 Zoom:", bg="#f0f0f0").pack(side=tk.LEFT)
        tk.Button(zoom_frame, text="+", command=self.app.zoom_in, width=3).pack(side=tk.LEFT, padx=2)
        tk.Button(zoom_frame, text="-", command=self.app.zoom_out, width=3).pack(side=tk.LEFT, padx=2)

        # ==== ステータスバー ====
        self.app.status = tk.Label(root, text="No PDF loaded", anchor="w", bg="#eaeaea", relief="sunken")
        self.app.status.pack(side=tk.BOTTOM, fill=tk.X)

        # ==== 屋根倍率プリセット UI ====
        slope_frame = tk.Frame(tb, bg="#f0f0f0")
        slope_frame.pack(side=tk.LEFT, padx=5)

        tk.Label(slope_frame, text="屋根倍率:", bg="#f0f0f0").pack(side=tk.LEFT)

        # combobox（過去の倍率リストを表示する）
        self.slope_combo = ttk.Combobox(
            slope_frame, width=6, state="readonly"
        )
        self.slope_combo.pack(side=tk.LEFT, padx=3)

        # + ボタン（新規倍率追加）
        tk.Button(
            slope_frame,
            text="+",
            width=2,
            command=self.app.add_new_slope_dialog
        ).pack(side=tk.LEFT)

        self.bind_slope_events()

    # =====================================================
    # 色切り替え・カスタムカラー選択
    # =====================================================
    def set_color(self, color):
        """固定色／基本色ボタン押下時"""
        self.app.current_color = color
        self.app.color_preview.config(bg=color)

    def choose_color(self):
        """カラーピッカーで色を選ぶ"""
        color_code = colorchooser.askcolor(title="色を選択")
        if color_code and color_code[1]:
            self.app.current_color = color_code[1]
            self.app.color_preview.config(bg=color_code[1])

    def bind_slope_events(self):
        self.slope_combo.bind("<<ComboboxSelected>>", self.on_slope_selected)

    def on_slope_selected(self, event):
        value = float(self.slope_combo.get())
        page = self.app.page_index

        s = self.app.selected_shape
        if s and s.get("color") == "#0000ff":  # 屋根
            s["slope"] = value
        else:
            self.app.page_slope_default[page] = value

        self.app.recalculate_page(page)
        self.app.display_page()
