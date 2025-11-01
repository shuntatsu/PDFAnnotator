# app_core.py
import tkinter as tk
from PIL import ImageTk
from tkinter import filedialog, messagebox
import json
from ui_toolbar import UIToolbar
from pdf_manager import PDFManager
from shape_manager import ShapeManager
from event_handlers import EventHandlers


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
        self.shapes_by_page = data["shapes_by_page"]
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
