# shape_manager.py
import uuid
import math
from utils_geometry import point_in_triangle, dist_point_to_segment

# =====================================================
# ShapeManager 本体
# =====================================================
class ShapeManager:
    def __init__(self, app):
        self.app = app
        self.triangle_points = []
        self.tri_preview_ids = []
        self.handles_ids = []
        self.handle_targets = []
        self.active_handle = None

    # =====================================================
    # 追加された append_shape
    # =====================================================
    def append_shape(self, s):
        """図形をページに追加し再描画"""
        self.app.shapes_by_page.setdefault(self.app.page_index, []).append(s)
        self.app.display_page(highlight_shape=s)

    # =====================================================
    # 図形描画・ハイライト
    # =====================================================
    def draw_shape(self, s, highlight=False):
        t = s["type"]
        cv = self.app.canvas
        color = s.get("color", "black")
        width = 3 if highlight else 2

        if t == "rect":
            x1, y1 = self.app.pdf_to_canvas(s["x"], s["y"])
            x2, y2 = self.app.pdf_to_canvas(s["x"] + s["w"], s["y"] + s["h"])
            cv.create_rectangle(x1, y1, x2, y2, outline=color, width=width)
            if highlight:
                self._draw_rect_handles(x1, y1, x2, y2)

        elif t == "ellipse":
            x1, y1 = self.app.pdf_to_canvas(s["x"], s["y"])
            x2, y2 = self.app.pdf_to_canvas(s["x"] + s["w"], s["y"] + s["h"])
            cv.create_oval(x1, y1, x2, y2, outline=color, width=width)
            if highlight:
                self._draw_ellipse_handles(x1, y1, x2, y2)

        elif t == "line":
            x1, y1 = self.app.pdf_to_canvas(s["x1"], s["y1"])
            x2, y2 = self.app.pdf_to_canvas(s["x2"], s["y2"])
            cv.create_line(x1, y1, x2, y2, fill=color, width=width)
            if highlight:
                self._draw_line_handles(x1, y1, x2, y2)

        elif t == "triangle":
            pts = [self.app.pdf_to_canvas(x, y) for x, y in s["points"]]
            cv.create_polygon(*[v for p in pts for v in p], outline=color, fill="", width=width)
            if highlight:
                self._draw_triangle_handles(pts)

        elif t == "text":
            x, y = self.app.pdf_to_canvas(s["x"], s["y"])
            cv.create_text(x, y, anchor="nw", text=s["text"], fill="black", font=("Arial", 14))
            if highlight:
                self._draw_rect_handles(x, y, x + 60, y + 25)

    # =====================================================
    # ハンドル描画（各形状）
    # =====================================================
    def _draw_handle(self, x, y, shape, idx):
        cv = self.app.canvas
        hs = 6
        hid = cv.create_rectangle(x - hs, y - hs, x + hs, y + hs, fill="white", outline="black")
        self.handles_ids.append(hid)
        self.handle_targets.append((hid, shape, idx))

    def _draw_rect_handles(self, x1, y1, x2, y2):
        for i, (x, y) in enumerate([(x1, y1), (x2, y1), (x2, y2), (x1, y2)]):
            self._draw_handle(x, y, self.app.selected_shape, i)

    def _draw_ellipse_handles(self, x1, y1, x2, y2):
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        pts = [(cx, y1), (x2, cy), (cx, y2), (x1, cy)]
        for i, (x, y) in enumerate(pts):
            self._draw_handle(x, y, self.app.selected_shape, i)

    def _draw_line_handles(self, x1, y1, x2, y2):
        for i, (x, y) in enumerate([(x1, y1), (x2, y2)]):
            self._draw_handle(x, y, self.app.selected_shape, i)

    def _draw_triangle_handles(self, pts):
        for i, (x, y) in enumerate(pts):
            self._draw_handle(x, y, self.app.selected_shape, i)

    # =====================================================
    # ハンドル検出
    # =====================================================
    def detect_handle(self, cx, cy):
        for hid, shape, idx in self.handle_targets:
            x1, y1, x2, y2 = self.app.canvas.coords(hid)
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                self.active_handle = (shape, idx)
                return True
        return False

    def clear_handles(self):
        for hid in self.handles_ids:
            self.app.canvas.delete(hid)
        self.handles_ids.clear()
        self.handle_targets.clear()
        self.active_handle = None

    # =====================================================
    # ハンドルによるリサイズ処理
    # =====================================================
    def resize_by_handle(self, shape, idx, cx, cy):
        t = shape["type"]
        px, py = self.app.canvas_to_pdf(cx, cy)

        if t == "rect":
            x, y, w, h = shape["x"], shape["y"], shape["w"], shape["h"]
            if idx == 0:  # 左上
                shape["w"] = (x + w) - px
                shape["h"] = (y + h) - py
                shape["x"], shape["y"] = px, py
            elif idx == 1:  # 右上
                shape["w"] = px - x
                shape["h"] = (y + h) - py
                shape["y"] = py
            elif idx == 2:  # 右下
                shape["w"] = px - x
                shape["h"] = py - y
            elif idx == 3:  # 左下
                shape["x"] = px
                shape["w"] = (x + w) - px
                shape["h"] = py - y

        elif t == "ellipse":
            x, y, w, h = shape["x"], shape["y"], shape["w"], shape["h"]
            if idx == 0:  # 上
                shape["y"] = py
                shape["h"] = (y + h) - py
            elif idx == 1:  # 右
                shape["w"] = px - x
            elif idx == 2:  # 下
                shape["h"] = py - y
            elif idx == 3:  # 左
                shape["x"] = px
                shape["w"] = (x + w) - px

        elif t == "line":
            if idx == 0:
                shape["x1"], shape["y1"] = px, py
            elif idx == 1:
                shape["x2"], shape["y2"] = px, py

        elif t == "triangle":
            shape["points"][idx] = (px, py)

        self.app.display_page(highlight_shape=shape)

    # =====================================================
    # 図形検出
    # =====================================================
    def find_shape(self, cx, cy):
        for s in reversed(self.app.shapes_by_page.get(self.app.page_index, [])):
            t = s["type"]
            if t == "rect":
                x1, y1 = self.app.pdf_to_canvas(s["x"], s["y"])
                x2, y2 = self.app.pdf_to_canvas(s["x"] + s["w"], s["y"] + s["h"])
                if dist_point_to_segment(cx, cy, x1, y1, x2, y1) < 6 or \
                   dist_point_to_segment(cx, cy, x2, y1, x2, y2) < 6 or \
                   dist_point_to_segment(cx, cy, x2, y2, x1, y2) < 6 or \
                   dist_point_to_segment(cx, cy, x1, y2, x1, y1) < 6:
                    return s, "edge"
                if x1 <= cx <= x2 and y1 <= cy <= y2:
                    return s, "inside"

            elif t == "ellipse":
                x1, y1 = self.app.pdf_to_canvas(s["x"], s["y"])
                x2, y2 = self.app.pdf_to_canvas(s["x"] + s["w"], s["y"] + s["h"])
                cx0, cy0 = (x1 + x2) / 2, (y1 + y2) / 2
                rx, ry = abs(x2 - x1) / 2, abs(y2 - y1) / 2
                d = ((cx - cx0)**2) / (rx**2) + ((cy - cy0)**2) / (ry**2)
                if abs(d - 1.0) < 0.05:
                    return s, "edge"
                if d < 1.0:
                    return s, "inside"

            elif t == "line":
                x1, y1 = self.app.pdf_to_canvas(s["x1"], s["y1"])
                x2, y2 = self.app.pdf_to_canvas(s["x2"], s["y2"])
                if dist_point_to_segment(cx, cy, x1, y1, x2, y2) < 6:
                    return s, "edge"

            elif t == "triangle":
                pts = [self.app.pdf_to_canvas(x, y) for x, y in s["points"]]
                if point_in_triangle((cx, cy), *pts):
                    return s, "inside"
                for i in range(3):
                    x1, y1 = pts[i]
                    x2, y2 = pts[(i + 1) % 3]
                    if dist_point_to_segment(cx, cy, x1, y1, x2, y2) < 6:
                        return s, "edge"

            elif t == "text":
                x, y = self.app.pdf_to_canvas(s["x"], s["y"])
                if abs(cx - x) < 60 and abs(cy - y) < 25:
                    return s, "inside"

        return None, None
    # ----------------------------
    # 三角形プレビュー
    # ----------------------------
    def show_triangle_preview(self, cx, cy):
        """三角形作成中に予測線を描画"""
        cv = self.app.canvas
        # 既存プレビュー削除
        for pid in self.tri_preview_ids:
            cv.delete(pid)
        self.tri_preview_ids.clear()

        pts = self.triangle_points
        if len(pts) >= 1:
            x1, y1 = pts[-1]
            self.tri_preview_ids.append(cv.create_line(x1, y1, cx, cy, fill="orange", dash=(4, 2), width=2))
        if len(pts) == 2:
            x0, y0 = pts[0]
            self.tri_preview_ids.append(cv.create_line(x0, y0, cx, cy, fill="orange", dash=(4, 2), width=2))

    def finalize_triangle(self):
        """三角形確定"""
        if len(self.triangle_points) == 3:
            pts_pdf = [self.app.canvas_to_pdf(x, y) for x, y in self.triangle_points]
            s = {"id": str(uuid.uuid4()), "type": "triangle", "points": pts_pdf}
            self.append_shape(s)
        # リセット
        for pid in self.tri_preview_ids:
            self.app.canvas.delete(pid)
        self.tri_preview_ids.clear()
        self.triangle_points.clear()
        
    # =====================================================
    # ハンドル削除  
    # =====================================================
    def detect_handle(self, cx, cy):
        """クリック位置(cx,cy)がハンドルに近いか判定"""
        if not hasattr(self, "handles_ids") or not self.handles_ids:
            return False

        valid_handles = []
        for hid in self.handles_ids:
            coords = self.app.canvas.coords(hid)
            if len(coords) == 4:  # 有効なハンドルだけ
                valid_handles.append(hid)
        self.handles_ids = valid_handles

        # shapeを確実に取得（前回選択状態を参照）
        shape = getattr(self.app, "selected_shape", None)
        if not shape:
            return False

        for idx, hid in enumerate(self.handles_ids):
            coords = self.app.canvas.coords(hid)
            if len(coords) != 4:
                continue
            x1, y1, x2, y2 = coords
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                self.active_handle = (shape, idx)
                return True

        return False
