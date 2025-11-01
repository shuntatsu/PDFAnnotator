# pdf_manager.py
import fitz
from PIL import Image, ImageTk

class PDFManager:
    def __init__(self, app):
        self.app = app

    # ---------- PDFを開く ----------
    def open_pdf(self, path):
        try:
            self.app.doc = fitz.open(path)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", str(e))
            return False
        self.app.pdf_path = path
        self.app.page_index = 0
        self.app.scale = 1.0
        self.app.offset_x = 0
        self.app.offset_y = 0
        self.app.display_page()
        return True

    # ---------- ページを描画 ----------
    def render_page(self):
        if not self.app.doc:
            return None
        page = self.app.doc.load_page(self.app.page_index)
        mat = fitz.Matrix(self.app.scale, self.app.scale)
        pix = page.get_pixmap(matrix=mat)
        return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # ---------- ページを進む・戻る ----------
    def next_page(self):
        if self.app.doc and self.app.page_index < len(self.app.doc) - 1:
            self.app.page_index += 1
            self.app.display_page()

    def prev_page(self):
        if self.app.doc and self.app.page_index > 0:
            self.app.page_index -= 1
            self.app.display_page()

    # ---------- PDF出力 ----------
    def export(self, save_path):
        if not self.app.doc:
            return
        out = fitz.open(self.app.pdf_path)
        for i in range(len(out)):
            p = out[i]
            for s in self.app.shapes_by_page.get(i, []):
                t = s["type"]
                if t == "rect":
                    p.draw_rect(fitz.Rect(s["x"],s["y"],s["x"]+s["w"],s["y"]+s["h"]),color=(1,0,0))
                elif t == "ellipse":
                    p.draw_ellipse(fitz.Rect(s["x"],s["y"],s["x"]+s["w"],s["y"]+s["h"]),color=(0,0,1))
                elif t == "line":
                    p.draw_line((s["x1"],s["y1"]),(s["x2"],s["y2"]),color=(0,1,0))
                elif t == "triangle":
                    pts=[fitz.Point(x,y) for x,y in s["points"]]
                    p.draw_polygon(pts,color=(1,0.5,0))
                elif t == "text":
                    p.insert_text((s["x"],s["y"]),s["text"],fontsize=12,color=(0,0,0))
        out.save(save_path)
