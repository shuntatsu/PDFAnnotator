import tkinter as tk
from PIL import ImageTk
from tkinter import filedialog, messagebox, simpledialog
import json
from ui_toolbar import UIToolbar
from pdf_manager import PDFManager
from shape_manager import ShapeManager
from event_handlers import EventHandlers, NumericInputDialog
import math_eval
import math

class PDFAnnotator:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Annotator")
        self.root.geometry("1100x1000")

        # ====== 状態 ======
        self.doc = None
        self.pdf_path = None
        self.page_index = 0
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.mode = "move"
        self.shape_type = None
        self.active_button = None
        self.selected_shape = None
        self.shapes_by_page = {}
        self.slope_presets = []   # [1.021, 1.05, ...] 過去に作った倍率記録
        self.page_slope_default = {} 

        # ====== Manager群 ======
        self.pdf = PDFManager(self)
        self.shapes = ShapeManager(self)
        self.ui = UIToolbar(self)
        self.handlers = EventHandlers(self)

        # ====== Canvas ======
        self.canvas = tk.Canvas(root, bg="#ddd")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # ====== ページ番号ラベル ======
        self.page_label = tk.Label(root, text="Page 0 / 0", bg="#eee")
        self.page_label.pack(side=tk.BOTTOM, fill=tk.X)

        # ====== Toolbar構築 ======
        self.ui.build_toolbar(root)

        # ====== イベント登録 ======
        self.canvas.bind("<ButtonPress-1>", self.handlers.on_press)
        self.canvas.bind("<B1-Motion>", self.handlers.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.handlers.on_release)
        self.canvas.bind("<Motion>", self.handlers.on_motion)
        self.canvas.bind("<Double-Button-1>", self.handlers.on_double_click)
        self.canvas.bind("<MouseWheel>", self.handlers.on_mousewheel)
        root.bind("<Delete>", self.delete_selected)
        root.bind("<BackSpace>", self.delete_selected)

    # ======================================================
    # ページ描画
    # ======================================================
    def display_page(self, highlight_shape=None):
        """PDF＋図形再描画（必要に応じて強調）"""
        if not self.doc:
            return
        img = self.pdf.render_page()
        if not img:
            return

        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, image=self.tk_img)

        # 図形描画
        for s in self.shapes_by_page.get(self.page_index, []):
            highlight = (s is highlight_shape or s is self.selected_shape)
            self.shapes.draw_shape(s, highlight=highlight)

        # ページラベル更新
        self.page_label.config(text=f"Page {self.page_index+1} / {len(self.doc)}")

        totals, formulas = self.calc_page_stats(self.page_index)

        txt = "\n".join(formulas)

        cx = 40
        cy = self.canvas.winfo_height() - (len(formulas) * 16) - 20

        self.canvas.create_text(
            cx,
            cy,
            anchor="nw",
            text=txt,
            fill="#333333",
            font=("Arial", 14)
        )

    # ======================================================
    # ファイル操作
    # ======================================================
    def open_pdf_dialog(self):
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if path:
            if self.pdf.open_pdf(path):
                self.set_status(f"Opened: {path}")
                self.display_page()

    def export_pdf_dialog(self):
        if not self.doc:
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf")
        if path:
            self.pdf.export(path)
            messagebox.showinfo("Exported", f"Saved: {path}")

    def save_project_dialog(self):
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if not path:
            return
        data = {"pdf_path": self.pdf_path, "shapes_by_page": self.shapes_by_page}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.set_status(f"Project saved: {path}")

    def load_project_dialog(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.pdf_path = data["pdf_path"]

        raw = data.get("shapes_by_page", {})
        self.shapes_by_page = {int(k): v for k, v in raw.items()}

        self.pdf.open_pdf(self.pdf_path)
        self.set_status(f"Project loaded: {path}")
        self.display_page()

    # ======================================================
    # ページ操作
    # ======================================================
    def next_page(self):
        if not self.doc:
            return
        if self.page_index < len(self.doc) - 1:
            self.page_index += 1
            self.selected_shape = None
            self.shapes.clear_handles()
            self.display_page()

    def prev_page(self):
        if not self.doc:
            return
        if self.page_index > 0:
            self.page_index -= 1
            self.selected_shape = None
            self.shapes.clear_handles()
            self.display_page()

    def delete_selected(self, event=None):
        """選択中図形 or ページ削除"""
        if self.selected_shape:
            lst = self.shapes_by_page.get(self.page_index, [])
            if self.selected_shape in lst:
                lst.remove(self.selected_shape)
                self.selected_shape = None
                self.shapes.clear_handles()
                self.display_page()
        else:
            if not self.doc:
                return
            if len(self.doc) > 1:
                self.doc.delete_page(self.page_index)
                self.page_index = min(self.page_index, len(self.doc) - 1)
                self.display_page()
            else:
                messagebox.showinfo("削除不可", "最後のページは削除できません。")

    # ======================================================
    # ズーム機能
    # ======================================================
    def zoom_in(self):
        self.scale *= 1.25
        self.display_page()

    def zoom_out(self):
        self.scale /= 1.25
        self.display_page()

    # ======================================================
    # モード切替
    # ======================================================
    def toggle_mode(self, btn, mode):
        """Move / Draw モード切替"""
        if self.active_button == btn:
            # 同じボタンを再クリック → OFF
            btn.config(bg="SystemButtonFace")
            self.mode = "move"
            self.active_button = None
        else:
            # 新しく押されたボタンをアクティブに
            if self.active_button:
                self.active_button.config(bg="SystemButtonFace")
            btn.config(bg="lightblue")
            self.mode = mode
            self.active_button = btn

        # ---- Moveモードに戻る時はShapeボタンOFF ----
        if self.mode == "move":
            self.shape_type = None
            if hasattr(self, "shape_buttons"):
                for b in self.shape_buttons.values():
                    b.config(bg="SystemButtonFace")
            if hasattr(self, "btn_draw"):
                self.btn_draw.config(bg="SystemButtonFace")

    def toggle_shape(self, shape):
        """図形選択時、自動的にDrawモードに切替"""
        if not hasattr(self, "shape_buttons"):
            return

        # ---- すべての図形ボタンをリセット ----
        for b in self.shape_buttons.values():
            b.config(bg="SystemButtonFace")

        btn = self.shape_buttons[shape]
        if self.shape_type == shape:
            # 同じ図形を再クリック → OFF & moveに戻す
            self.shape_type = None
            btn.config(bg="SystemButtonFace")
            self.mode = "move"
            if hasattr(self, "btn_draw"):
                self.btn_draw.config(bg="SystemButtonFace")
        else:
            # 新しい図形選択
            self.shape_type = shape
            btn.config(bg="lightblue")
            self.mode = "draw"

            # MoveボタンはOFF、DrawをONに
            if hasattr(self, "btn_move"):
                self.btn_move.config(bg="SystemButtonFace")
            if hasattr(self, "btn_draw"):
                self.btn_draw.config(bg="lightblue")

    # ======================================================
    # ユーティリティ
    # ======================================================
    def set_status(self, msg: str):
        if hasattr(self, "status"):
            self.status.config(text=msg)

    def canvas_to_pdf(self, cx, cy):
        return (cx - self.offset_x) / self.scale, (cy - self.offset_y) / self.scale

    def pdf_to_canvas(self, px, py):
        return px * self.scale + self.offset_x, py * self.scale + self.offset_y
    
    def add_new_slope_dialog(self):
        # H と B を一気に聞く（既存の NumericInputDialog を再利用）
        dlg = NumericInputDialog(self.root, "屋根倍率の計算", ["高さ H", "底 B"])
        vals = getattr(dlg, "result", {}) or {}

        H = vals.get("高さ H")
        B = vals.get("底 B")

        # キャンセル or 入力不正
        if H is None or B is None:
            return

        try:
            raw = math.sqrt(H * H + B * B) / B
            slope = math_eval.truncate_3(raw)  # 4.2325 → 4.232 みたいな切り捨て
        except Exception:
            messagebox.showerror("エラー", "正しい数値を入力してください")
            return

        # プリセットに保存（重複は追加しない）
        if slope not in self.slope_presets:
            self.slope_presets.append(slope)
            self.slope_presets.sort()

        # UI 更新
        self.update_slope_combo()

        # 選択中 shape が屋根なら個別倍率
        s = self.selected_shape
        if s and s.get("color") == "#0000ff":  # 屋根色
            s["slope"] = slope
        else:
            # ページデフォルト
            self.page_slope_default[self.page_index] = slope

        self.display_page()

    def update_slope_combo(self):
        items = [f"{v:.3f}" for v in self.slope_presets]
        self.ui.slope_combo["values"] = items

        # 現在のページデフォルトを表示
        current = self.page_slope_default.get(self.page_index, None)
        if current:
            self.ui.slope_combo.set(f"{current:.3f}")
        else:
            self.ui.slope_combo.set("")

    def calc_page_stats(self, page_index):
        """ページ内の図形を集計し、数値と式の情報を返す"""
        shapes = self.shapes_by_page.get(page_index, [])

        # 色 → 属性名
        ATTR = {
            "#ff0000": "wall",
            "#0000ff": "roof",
            "#00aa00": "bshita",
            "#ffa500": "koya",
            "#800080": "window",
            "#999999": "door",
        }

        # 集計値
        totals = {k: 0.0 for k in ["wall", "roof", "bshita", "koya", "window", "door"]}

        # 式一覧（右下に描く用）
        formula_lines = []

        for s in shapes:
            col = s.get("color")
            val = s.get("value")

            if col not in ATTR or val is None:
                continue

            atr = ATTR[col]

            # --- 屋根だけは倍率をかける ---
            if atr == "roof":
                slope = self.shapes.get_slope_factor(s)
                result = val * slope
                totals["roof"] += result
                formula_lines.append(f"屋根: {val:.3f} × {slope:.3f} = {result:.3f}")
            else:
                totals[atr] += val
                formula_lines.append(f"{atr}: {val:.3f}")

        # --- 壁は窓・ドアを引く ---
        wall_final = totals["wall"] - (totals["window"] + totals["door"])
        formula_lines.append(
            f"壁最終: {totals['wall']:.3f} - ({totals['window']:.3f} + {totals['door']:.3f}) = {wall_final:.3f}"
        )
        totals["wall_final"] = wall_final

        return totals, formula_lines

    def calc_total_stats(self):
        pages = sorted(self.shapes_by_page.keys())

        grand = {
            "wall_final": 0.0,
            "roof": 0.0,
            "bshita": 0.0,
            "koya": 0.0,
            "window": 0.0,
            "door": 0.0,
        }

        all_formulas = []

        for p in pages:
            totals, formulas = self.calc_page_stats(p)
            if not formulas:
                continue
            all_formulas.append(f"=== Page {p+1} ===")
            all_formulas.extend(formulas)

            for k in grand:
                if k in totals:
                    grand[k] += totals[k]

        return grand, all_formulas

    def show_total_stats_dialog(self):
        total, formulas = self.calc_total_stats()

        txt = "\n".join(formulas)
        txt += "\n\n=== 総合集計 ===\n"

        for k, v in total.items():
            txt += f"{k}: {v:.3f}\n"

        messagebox.showinfo("総合集計", txt)

    # ======================================================
    # ページ集計テキストを追加（壁ページのみ）
    # ======================================================
    def add_summary_text_to_page(self, page_index=None):
        """calc_page_stats の結果をページに text 図形として追加する（壁ページのみ）"""
        import uuid

        if page_index is None:
            page_index = self.page_index

        totals, formulas = self.calc_page_stats(page_index)
        
        # === ここが printf 形式の文字列 ===
        txt = self.build_summary_string(totals, formulas, page_index)

        print("\n===== Page Summary (printf 出力) =====")
        print(txt)
        print("=====================================\n")

        # キャンバス高さ取得（適当な右下）
        self.root.update_idletasks()
        canvas_h = self.canvas.winfo_height() or 800

        cx = 40
        cy = canvas_h - (len(formulas) * 16) - 20
        px, py = self.canvas_to_pdf(cx, cy)

        shape = {
            "id": str(uuid.uuid4()),
            "type": "text",
            "x": px,
            "y": py,
            "text": txt,
            "color": "#333333",
            "summary": True,
        }

        self.shapes_by_page.setdefault(page_index, []).append(shape)

        if page_index == self.page_index:
            self.display_page()

    # ======================================================
    # 総合集計＋ページ集計テキスト表示
    # ======================================================
    def run_total_and_page_summary(self):
        """総合集計ダイアログ→現在ページに壁ページ集計textを置く"""
        self.show_total_stats_dialog()
        self.add_summary_text_to_page()

    def run_total_and_all_page_summary(self):
        """総合集計＋全ページに壁ページ集計テキストを追加"""
        self.show_total_stats_dialog()
        for p in sorted(self.shapes_by_page.keys()):
            self.add_summary_text_to_page(p)

    def build_summary_string(self, totals, formulas, page_index):
        """ページ集計結果を printf 風に読みやすい文字列に整形"""
        lines = []
        lines.append(f"[Page {page_index+1} 集計]")
        lines.append("")

        # 個別式（フォーミュラ）
        for f in formulas:
            lines.append(f)

        # 空行
        lines.append("")

        # 壁最終（printf 風）
        wall = totals["wall"]
        win  = totals["window"]
        door = totals["door"]
        wall_final = totals["wall_final"]

        lines.append("壁 有効面積 = 壁 −（ドア＋窓）")
        lines.append(f"             = {wall:.3f} − ({door:.3f} + {win:.3f})")
        lines.append(f"             = {wall_final:.3f}")

        return "\n".join(lines)