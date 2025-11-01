# event_handlers.py
import uuid
from tkinter import simpledialog

class EventHandlers:
    def __init__(self, app):
        self.app = app
        self.dragging = False
        self.drag_target = None
        self.drag_mode = None  # "move" or "resize"
        self.last_cx = None
        self.last_cy = None
        self.dragging_pdf = False
        self.drag_start = None

        # 図形生成関連
        self.pending_rect_start = None
        self.rect_preview_id = None
        self.triangle_first_line_id = None
        self.temp_line_id = None

    # =====================================================
    # マウス押下
    # =====================================================
    def on_press(self, e):
        if not self.app.doc:
            return
        cx, cy = e.x, e.y
        app = self.app

        # ------------------------
        # Moveモード（図形／PDF移動・リサイズ）
        # ------------------------
        if app.mode == "move":
            # ハンドルクリック（頂点・端点チェック）
            if hasattr(app.shapes, "detect_handle") and app.shapes.detect_handle(cx, cy):
                shape, idx = app.shapes.active_handle
                app.selected_shape = shape
                self.drag_target = (shape, idx)
                self.drag_mode = "resize"
                self.dragging = True
                return

            # 図形クリック
            shape, area = app.shapes.find_shape(cx, cy)
            if shape:
                app.selected_shape = shape
                self.dragging = True
                self.drag_target = shape
                self.drag_mode = "move" if area == "inside" else "resize"
                self.last_cx, self.last_cy = cx, cy
                app.display_page(highlight_shape=shape)
            else:
                # PDF全体の移動
                app.selected_shape = None
                self.dragging_pdf = True
                self.drag_start = (cx, cy)
                app.display_page()

        # ------------------------
        # Drawモード（図形生成）
        # ------------------------
        elif app.mode == "draw":
            stype = app.shape_type
            if not stype:
                return

            # ---- Rect（2クリック）----
            if stype == "rect":
                if not self.pending_rect_start:
                    self.pending_rect_start = (cx, cy)
                else:
                    x1, y1 = self.pending_rect_start
                    x2, y2 = cx, cy
                    left, right = sorted([x1, x2])
                    top, bottom = sorted([y1, y2])
                    px1, py1 = app.canvas_to_pdf(left, top)
                    px2, py2 = app.canvas_to_pdf(right, bottom)
                    s = {
                        "id": str(uuid.uuid4()),
                        "type": "rect",
                        "x": px1,
                        "y": py1,
                        "w": px2 - px1,
                        "h": py2 - py1,
                        "color": "red",
                    }
                    app.shapes.append_shape(s)
                    if self.rect_preview_id:
                        app.canvas.delete(self.rect_preview_id)
                        self.rect_preview_id = None
                    self.pending_rect_start = None

            # ---- Ellipse（1クリック）----
            elif stype == "ellipse":
                radius = 40
                px, py = app.canvas_to_pdf(cx - radius, cy - radius)
                size_pdf = radius * 2 / app.scale
                s = {
                    "id": str(uuid.uuid4()),
                    "type": "ellipse",
                    "x": px,
                    "y": py,
                    "w": size_pdf,
                    "h": size_pdf,
                    "color": "blue",
                }
                app.shapes.append_shape(s)

            # ---- Line（ドラッグで作成）----
            elif stype == "line":
                self.start_x, self.start_y = cx, cy
                self.temp_line_id = app.canvas.create_line(cx, cy, cx, cy, fill="green", width=2)

            # ---- Triangle（3クリック）----
            elif stype == "triangle":
                app.shapes.triangle_points.append((cx, cy))
                pts = app.shapes.triangle_points
                if len(pts) == 2:
                    (x1, y1), (x2, y2) = pts
                    if self.triangle_first_line_id:
                        app.canvas.delete(self.triangle_first_line_id)
                    self.triangle_first_line_id = app.canvas.create_line(x1, y1, x2, y2, fill="orange", width=2)
                elif len(pts) == 3:
                    pts_pdf = [app.canvas_to_pdf(x, y) for x, y in pts]
                    s = {"id": str(uuid.uuid4()), "type": "triangle", "points": pts_pdf, "color": "orange"}
                    app.shapes.append_shape(s)
                    # プレビュー削除
                    if self.triangle_first_line_id:
                        app.canvas.delete(self.triangle_first_line_id)
                        self.triangle_first_line_id = None
                    for pid in app.shapes.tri_preview_ids:
                        app.canvas.delete(pid)
                    app.shapes.triangle_points.clear()
                    app.shapes.tri_preview_ids.clear()

            # ---- Text ----
            elif stype == "text":
                txt = simpledialog.askstring("テキスト入力", "内容を入力:")
                if txt:
                    px, py = app.canvas_to_pdf(cx, cy)
                    s = {
                        "id": str(uuid.uuid4()),
                        "type": "text",
                        "x": px,
                        "y": py,
                        "w": 80,
                        "h": 20,
                        "text": txt,
                        "color": "black",
                    }
                    app.shapes.append_shape(s)

    # =====================================================
    # マウスドラッグ中
    # =====================================================
    def on_drag(self, e):
        cx, cy = e.x, e.y
        app = self.app

        # --- Moveモード ---
        if app.mode == "move":
            # ハンドルで頂点や端点をリサイズ
            if self.drag_mode == "resize" and isinstance(self.drag_target, tuple):
                shape, idx = self.drag_target
                app.shapes.resize_by_handle(shape, idx, cx, cy)
                return

            # 図形全体移動
            if self.dragging and self.drag_target:
                s = self.drag_target
                dx = (cx - self.last_cx) / app.scale
                dy = (cy - self.last_cy) / app.scale
                self.last_cx, self.last_cy = cx, cy
                t = s["type"]

                if t in ("rect", "ellipse", "text"):
                    s["x"] += dx
                    s["y"] += dy
                elif t == "line":
                    s["x1"] += dx; s["y1"] += dy
                    s["x2"] += dx; s["y2"] += dy
                elif t == "triangle":
                    s["points"] = [(x + dx, y + dy) for x, y in s["points"]]

                app.display_page(highlight_shape=s)

            # PDF移動
            elif self.dragging_pdf and self.drag_start:
                dx = cx - self.drag_start[0]
                dy = cy - self.drag_start[1]
                app.offset_x += dx
                app.offset_y += dy
                self.drag_start = (cx, cy)
                app.display_page()

        # --- Drawモード（線プレビュー）---
        elif app.mode == "draw" and app.shape_type == "line" and self.temp_line_id:
            app.canvas.coords(self.temp_line_id, self.start_x, self.start_y, cx, cy)

    # =====================================================
    # マウス離す（確定）
    # =====================================================
    def on_release(self, e):
        cx, cy = e.x, e.y
        app = self.app

        # 線を確定
        if app.mode == "draw" and app.shape_type == "line" and self.temp_line_id:
            x1, y1, x2, y2 = app.canvas.coords(self.temp_line_id)
            app.canvas.delete(self.temp_line_id)
            self.temp_line_id = None
            px1, py1 = app.canvas_to_pdf(x1, y1)
            px2, py2 = app.canvas_to_pdf(x2, y2)
            s = {"id": str(uuid.uuid4()), "type": "line", "x1": px1, "y1": py1, "x2": px2, "y2": py2, "color": "green"}
            app.shapes.append_shape(s)

        # 状態リセット
        self.dragging = False
        self.drag_target = None
        self.drag_mode = None
        self.dragging_pdf = False
        self.drag_start = None
        app.shapes.active_handle = None

    # =====================================================
    # マウス移動中（プレビュー）
    # =====================================================
    def on_motion(self, e):
        cx, cy = e.x, e.y
        app = self.app

        if app.mode == "draw" and app.shape_type == "rect" and self.pending_rect_start:
            x1, y1 = self.pending_rect_start
            x2, y2 = cx, cy
            if self.rect_preview_id:
                app.canvas.coords(self.rect_preview_id, x1, y1, x2, y2)
            else:
                self.rect_preview_id = app.canvas.create_rectangle(x1, y1, x2, y2, outline="red", dash=(4, 3))

        elif app.mode == "draw" and app.shape_type == "triangle":
            app.shapes.show_triangle_preview(cx, cy)

    # =====================================================
    # ホイールズーム
    # =====================================================
    def on_mousewheel(self, e):
        if e.delta > 0:
            self.app.zoom_in()
        else:
            self.app.zoom_out()

    # =====================================================
    # ダブルクリック（テキスト編集）
    # =====================================================
    def on_double_click(self, e):
        cx, cy = e.x, e.y
        s, _ = self.app.shapes.find_shape(cx, cy)
        if s and s["type"] == "text":
            new = simpledialog.askstring("編集", "新しいテキスト:", initialvalue=s["text"])
            if new:
                s["text"] = new
                self.app.display_page()
