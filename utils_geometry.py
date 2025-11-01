# utils_geometry.py
import math

# =====================================================
# 幾何ユーティリティ
# =====================================================
def dist_point_to_segment(px, py, x1, y1, x2, y2):
    """点(px,py)と線分(x1,y1)-(x2,y2)の距離"""
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    nx, ny = x1 + t * dx, y1 + t * dy
    return math.hypot(px - nx, py - ny)


def point_in_triangle(pt, v1, v2, v3):
    """点ptが三角形内か"""
    x, y = pt
    x1, y1 = v1
    x2, y2 = v2
    x3, y3 = v3
    denom = (y2 - y3)*(x1 - x3) + (x3 - x2)*(y1 - y3)
    if denom == 0:
        return False
    a = ((y2 - y3)*(x - x3) + (x3 - x2)*(y - y3)) / denom
    b = ((y3 - y1)*(x - x3) + (x1 - x3)*(y - y3)) / denom
    c = 1 - a - b
    return 0 <= a <= 1 and 0 <= b <= 1 and 0 <= c <= 1