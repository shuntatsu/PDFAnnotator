# shape_manager.py
import uuid
import math
from utils_geometry import point_in_triangle, dist_point_to_segment
from math_eval import MathEvalError, eval_and_truncate_3

class ShapeManager:
    def __init__(self, app):
        self.app = app
        self.triangle_points = []
        self.tri_preview_ids = []
        self.handles_ids = []
        self.handle_targets = []
        self.active_handle = None
        self.shapes = [] 

    # =====================================================
    # 図形追加
    # =====================================================
    def append_shape(self, s):
        """図形をページに追加して再描画"""
        self.update_shape_value(s)
        s.setdefault("color", "black")
        self.app.shapes_by_page.setdefault(self.app.page_index, []).append(s)
        self.app.display_page(highlight_shape=s)

    # =====================================================
    # 図形描画
    # =====================================================
    def draw_shape(self, s, highlight=False):
        t = s["type"]
        cv = self.app.canvas
        color = s.get("color", self.app.current_color)
        width = 3 if highlight else 2
        scale = self.app.scale

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
            size = max(10, int(14 * scale))

            tid = cv.create_text(
                x, y, anchor="nw",
                text=s["text"],
                fill=color,
                font=("Arial", size)
            )

            # --- 選択時だけハンドルつきの枠を描く ---
            if highlight:
                # テキストの実際の矩形領域を取得
                x1, y1, x2, y2 = cv.bbox(tid)

                # 枠線を描く
                cv.create_rectangle(x1, y1, x2, y2, outline=color, width=2)

                # ハンドル（四隅）
                self._draw_rect_handles(x1, y1, x2, y2)

    # =====================================================
    # 計算式を同色で追加（図形近くに配置）
    # =====================================================
    def create_formula_text(self, s, text, color):
        t = s["type"]
        app = self.app

        # --- テキストの配置位置を図形タイプ別に決定 ---
        if t == "triangle":
            pts = s["points"]
            avg_x = sum(x for x, _ in pts) / 3
            avg_y = sum(y for _, y in pts) / 3 - 20
            tx, ty = avg_x, avg_y
        elif t == "line":
            tx = (s["x1"] + s["x2"]) / 2
            ty = (s["y1"] + s["y2"]) / 2 - 10
        else:
            tx = s.get("x", 0) + s.get("w", 60)
            ty = s.get("y", 0) - 15

        t_text = {
            "id": str(uuid.uuid4()),
            "type": "text",
            "x": tx,
            "y": ty,
            "text": text,
            "color": color,
        }
        self.append_shape(t_text)

    # =====================================================
    # ハンドル描画（各形状タイプごと）
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
        """クリック位置(cx, cy)がハンドル上か判定"""
        if not hasattr(self, "handles_ids") or not self.handles_ids:
            return False

        valid_handles = []
        for hid in self.handles_ids:
            coords = self.app.canvas.coords(hid)
            if len(coords) == 4:  # 有効なハンドルのみ
                valid_handles.append(hid)
        self.handles_ids = valid_handles

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

    # =====================================================
    # ハンドル削除
    # =====================================================
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
            if idx == 0:
                shape["y"] = py
                shape["h"] = (y + h) - py
            elif idx == 1:
                shape["w"] = px - x
            elif idx == 2:
                shape["h"] = py - y
            elif idx == 3:
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
        self.app.shapes.update_shape_value(shape)

    # =====================================================
    # 図形クリック検出（選択判定）
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
                d = ((cx - cx0) ** 2) / (rx ** 2) + ((cy - cy0) ** 2) / (ry ** 2)
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
                size = int(14 * self.app.scale)

                # 1) 仮の text を描いて bbox を取得
                tid = self.app.canvas.create_text(
                    x, y,
                    anchor="nw",
                    text=s["text"],
                    font=("Arial", size),
                    fill=s.get("color", "black"),
                )
                x1, y1, x2, y2 = self.app.canvas.bbox(tid)
                self.app.canvas.delete(tid)

                # 2) クリック座標が bbox に入っていればヒット
                if x1 <= cx <= x2 and y1 <= cy <= y2:
                    return s, "inside"

        return None, None

    # =====================================================
    # 三角形プレビュー
    # =====================================================
    def show_triangle_preview(self, cx, cy):
        """三角形作成中に予測線を表示"""
        cv = self.app.canvas
        for pid in self.tri_preview_ids:
            cv.delete(pid)
        self.tri_preview_ids.clear()

        pts = self.triangle_points
        if len(pts) >= 1:
            x1, y1 = pts[-1]
            self.tri_preview_ids.append(
                cv.create_line(x1, y1, cx, cy, fill="orange", dash=(4, 2), width=2)
            )
        if len(pts) == 2:
            x0, y0 = pts[0]
            self.tri_preview_ids.append(
                cv.create_line(x0, y0, cx, cy, fill="orange", dash=(4, 2), width=2)
            )

    # =====================================================
    # value（面積・長さ・計算結果）を更新する汎用関数（完全版）
    # =====================================================
    def update_shape_value(self, s):
        if not s:
            return

        t = s.get("type")

        # -------------------------------------------
        # 図形タイプが text 以外で、
        # ユーザー入力で value を固定している場合は上書きしない
        # （手入力した寸法・面積を尊重する）
        # -------------------------------------------
        if t != "text" and s.get("manual_value"):
            return

        # ===========================
        #  TEXT（数式評価もここで統一）
        # ===========================
        if t == "text":
            raw = s.get("text", "")
            if raw is None:
                s["value"] = None
                return

            raw = raw.strip()
            if raw == "":
                s["value"] = None
                return

            # "= のついた式は表示形式（例: '5+3=' → '5+3=8'）
            if raw.endswith("="):
                expr = raw[:-1]
                try:
                    val = eval_and_truncate_3(expr)
                    # 表示を常に正しい計算式に更新
                    s["text"] = f"{expr}={val}"
                    s["value"] = val
                except MathEvalError:
                    # 表示はそのまま、value だけ None
                    s["value"] = None
                return

            # "= なしの純粋な式"
            try:
                val = eval_and_truncate_3(raw)
                # 表示を計算結果にそろえる
                s["text"] = str(val)
                s["value"] = val
            except MathEvalError:
                # 数式でない → 単なるメモ扱い
                s["value"] = None

            return

        # ===========================
        #  RECT（面積）
        # ===========================
        if t == "rect":
            w = abs(s.get("w", 0))
            h = abs(s.get("h", 0))
            area = w * h
            s["value"] = round(area, 5)
            return

        # ===========================
        #  ELLIPSE（円/楕円の面積）
        # ===========================
        if t == "ellipse":
            w = abs(s.get("w", 0))
            h = abs(s.get("h", 0))
            r1 = w / 2
            r2 = h / 2
            area = math.pi * r1 * r2
            s["value"] = round(area, 5)
            return

        # ===========================
        #  LINE（長さ）
        # ===========================
        if t == "line":
            x1, y1 = s.get("x1"), s.get("y1")
            x2, y2 = s.get("x2"), s.get("y2")

            if None in (x1, y1, x2, y2):
                s["value"] = None
                return

            dx = x2 - x1
            dy = y2 - y1
            length = math.sqrt(dx * dx + dy * dy)
            s["value"] = round(length, 5)
            return

        # ===========================
        #  TRIANGLE（三角形の3点）
        # ===========================
        if t == "triangle":
            pts = s.get("points")
            if not pts or len(pts) != 3:
                s["value"] = None
                return

            try:
                (x1, y1), (x2, y2), (x3, y3) = pts
                area = abs(
                    (x1 * (y2 - y3)
                     + x2 * (y3 - y1)
                     + x3 * (y1 - y2)) / 2.0
                )
                s["value"] = round(area, 5)
            except Exception:
                s["value"] = None
            return

        # ===========================
        #  フォールバック（メモなど）
        # ===========================
        s["value"] = None

    def get_slope_factor(self, s, page_index=None):
        """屋根の倍率を返す。shape 個別設定 > ページデフォルト > 1.0"""
        if not s:
            return 1.0

        # shape 個別設定があれば優先
        slope = s.get("slope")
        if slope is not None:
            return slope

        # ページデフォルト
        if page_index is None:
            # 呼び出し元からページ指定が無いときは、現在ページを使う
            page = self.app.page_index
        else:
            page = page_index

        return self.app.page_slope_default.get(page, 1.0)

