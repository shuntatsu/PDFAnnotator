import uuid
import tkinter as tk
from tkinter import simpledialog


# =====================================================
# 数値入力フォーム（複数項目対応・Enter/Esc対応）
# =====================================================
class NumericInputDialog(simpledialog.Dialog):
    """複数数値を入力できる汎用ダイアログ"""
    def __init__(self, parent, title, fields):
        self.fields = fields
        self.result = {}  # super()の後に初期化（Dialogが上書きするため）
        super().__init__(parent, title)

    def body(self, master):
        self.entries = {}
        for i, label in enumerate(self.fields):
            tk.Label(master, text=label + ":", anchor="w").grid(
                row=i, column=0, padx=5, pady=4, sticky="w"
            )
            e = tk.Entry(master)
            e.grid(row=i, column=1, padx=5, pady=4)
            self.entries[label] = e

        # --- キーバインド ---
        master.bind("<Return>", lambda event: self.ok())
        master.bind("<Escape>", lambda event: self.cancel())

        return list(self.entries.values())[0] if self.entries else None

    def apply(self):
        """OK時に入力値をfloatとして保存"""
        if self.result is None:
            self.result = {}
        for k, e in self.entries.items():
            try:
                self.result[k] = float(e.get())
            except ValueError:
                self.result[k] = None


# =====================================================
# イベントハンドラ本体
# =====================================================
class EventHandlers:
    def __init__(self, app):
        self.app = app
        self.pending_rect_start = None
        self.rect_preview_id = None
        self.temp_line_id = None
        self.triangle_first_line_id = None
        self.dragging = False
        self.drag_target = None
        self.drag_mode = None
        self.dragging_pdf = False
        self.drag_start = None

    # =====================================================
    # マウス押下（描画・移動など）
    # =====================================================
    def on_press(self, e):
        app = self.app
        if not app.doc:
            return
        cx, cy = e.x, e.y

        # ========================================
        # Drawモード：図形追加
        # ========================================
        if app.mode == "draw":
            t = app.shape_type
            if not t:
                return
    
            # ハンドルで頂点や端点をリサイズ
            if self.drag_mode == "resize" and isinstance(self.drag_target, tuple):
                shape, idx = self.drag_target
                app.shapes.resize_by_handle(shape, idx, cx, cy)
                return

            # ---- Rect ----
            if t == "rect":
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
                        "color": app.current_color,
                    }
                    app.shapes.append_shape(s)
                    self._show_formula_input(s)
                    if self.rect_preview_id:
                        app.canvas.delete(self.rect_preview_id)
                        self.rect_preview_id = None
                    self.pending_rect_start = None

            # ---- Ellipse ----
            elif t == "ellipse":
                r = 40
                px, py = app.canvas_to_pdf(cx - r, cy - r)
                size_pdf = r * 2 / app.scale
                s = {
                    "id": str(uuid.uuid4()),
                    "type": "ellipse",
                    "x": px,
                    "y": py,
                    "w": size_pdf,
                    "h": size_pdf,
                    "color": app.current_color,
                }
                app.shapes.append_shape(s)
                self._show_formula_input(s)

            # ---- Line ----
            elif t == "line":
                self.start_x, self.start_y = cx, cy
                self.temp_line_id = app.canvas.create_line(
                    cx, cy, cx, cy, fill=app.current_color, width=2
                )

            # ---- Triangle ----
            elif t == "triangle":
                app.shapes.triangle_points.append((cx, cy))
                pts = app.shapes.triangle_points
                if len(pts) == 2:
                    (x1, y1), (x2, y2) = pts
                    if self.triangle_first_line_id:
                        app.canvas.delete(self.triangle_first_line_id)
                    self.triangle_first_line_id = app.canvas.create_line(
                        x1, y1, x2, y2, fill=app.current_color, width=2
                    )
                elif len(pts) == 3:
                    pts_pdf = [app.canvas_to_pdf(x, y) for x, y in pts]
                    s = {
                        "id": str(uuid.uuid4()),
                        "type": "triangle",
                        "points": pts_pdf,
                        "color": app.current_color,
                    }
                    app.shapes.append_shape(s)
                    self._show_formula_input(s)
                    app.shapes.triangle_points.clear()
                    if self.triangle_first_line_id:
                        app.canvas.delete(self.triangle_first_line_id)
                        self.triangle_first_line_id = None

            elif t == "text":
                px, py = app.canvas_to_pdf(cx, cy)
                txt = simpledialog.askstring("テキスト入力", "内容を入力してください:", initialvalue="")
                if txt:
                    s = {
                        "id": str(uuid.uuid4()),
                        "type": "text",
                        "x": px,
                        "y": py,
                        "text": txt,
                        "color": app.current_color,
                    }
                app.shapes.append_shape(s)

        # ========================================
        # Moveモード：図形・PDF移動など
        # ========================================
        elif app.mode == "move":
            shape, area = app.shapes.find_shape(cx, cy)
            if shape:
                app.selected_shape = shape
                self.dragging = True
                self.drag_target = shape
                self.drag_mode = "move" if area == "inside" else "resize"
                self.last_cx, self.last_cy = cx, cy
                app.display_page(highlight_shape=shape)
            else:
                app.selected_shape = None
                self.dragging_pdf = True
                self.drag_start = (cx, cy)
                app.display_page()

    # =====================================================
    # 入力UI＋数式生成
    # =====================================================
    def _show_formula_input(self, s):
        """図形配置後に寸法入力を求めて数式を生成し、図形近くに表示"""
        t = s["type"]
        app = self.app
        color = s.get("color", app.current_color)
        formula = None

        if t == "rect":
            dlg = NumericInputDialog(app.root, "長方形の寸法入力", ["幅", "高さ"])
            vals = getattr(dlg, "result", {}) or {}
            w, h = vals.get("幅"), vals.get("高さ")
            if w and h:
                formula = f"{w:.2f} × {h:.2f} = {w*h:.2f}"

        elif t == "ellipse":
            dlg = NumericInputDialog(app.root, "円の寸法入力", ["半径"])
            vals = getattr(dlg, "result", {}) or {}
            r = vals.get("半径")
            if r:
                area = 3.14 * r * r
                formula = f"3.14×{r:.2f}×{r:.2f} = {area:.2f}"

        elif t == "triangle":
            dlg = NumericInputDialog(app.root, "三角形の寸法入力", ["底辺", "高さ"])
            vals = getattr(dlg, "result", {}) or {}
            base, h = vals.get("底辺"), vals.get("高さ")
            if base and h:
                area = base * h / 2
                formula = f"({base:.2f}×{h:.2f})/2 = {area:.2f}"

        if formula:
            print("Generated formula:", formula)
            app.shapes.create_formula_text(s, formula, color)

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
    # マウス離す（線確定など）
    # =====================================================
    def on_release(self, e):
        app = self.app
        cx, cy = e.x, e.y

        if app.mode == "draw" and app.shape_type == "line" and self.temp_line_id:
            x1, y1, x2, y2 = app.canvas.coords(self.temp_line_id)
            app.canvas.delete(self.temp_line_id)
            self.temp_line_id = None
            px1, py1 = app.canvas_to_pdf(x1, y1)
            px2, py2 = app.canvas_to_pdf(x2, y2)
            s = {
                "id": str(uuid.uuid4()),
                "type": "line",
                "x1": px1,
                "y1": py1,
                "x2": px2,
                "y2": py2,
                "color": app.current_color,
            }
            app.shapes.append_shape(s)
            self._show_formula_input(s)

        self.dragging = False
        self.drag_target = None
        self.dragging_pdf = False
        self.drag_start = None

    # =====================================================
    # マウス移動中（プレビュー）
    # =====================================================
    def on_motion(self, e):
        app = self.app
        cx, cy = e.x, e.y
        if app.mode == "draw" and app.shape_type == "rect" and self.pending_rect_start:
            x1, y1 = self.pending_rect_start
            if self.rect_preview_id:
                app.canvas.coords(self.rect_preview_id, x1, y1, cx, cy)
            else:
                self.rect_preview_id = app.canvas.create_rectangle(
                    x1, y1, cx, cy, outline=app.current_color, dash=(4, 3)
                )

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
