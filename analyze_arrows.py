import os
import math
from collections import defaultdict

# Import heuristics from the main module
import color_change2 as cc
import ezdxf

DXF_PATH = r"c:\Users\matheusr\Documents\Layers_e_Cotas\ref\pilar treliçacdo.dxf"

def point_dist(p1, p2):
    return math.hypot(p1[0]-p2[0], p1[1]-p2[1])

def polyline_length_from_points(points):
    if not points:
        return 0.0
    total = 0.0
    prev = points[0]
    for p in points[1:]:
        total += point_dist(prev, p)
        prev = p
    return total


def analyze(path):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()

    counts = defaultdict(int)
    arrow_counts = defaultdict(int)
    lengths = []  # tuples (length, dxftype, handle, is_arrow)

    for ent in msp:
        try:
            dx = ent.dxftype()
        except Exception:
            continue
        if dx not in ('LINE', 'TRACE'):
            continue
        counts[dx] += 1
        # compute length
        length = None
        if dx == 'LINE':
            try:
                s = ent.dxf.start
                e = ent.dxf.end
                length = point_dist(s, e)
            except Exception:
                # fallback to bbox max dim
                w, h = cc.get_entity_bbox_size(ent)
                length = max(w or 0.0, h or 0.0)
        elif dx == 'TRACE':
            # try to get points sequence
            pts = None
            try:
                pts = list(ent.vertices_in_wcs())
            except Exception:
                try:
                    pts = list(ent.points())
                except Exception:
                    pts = None
            if pts:
                length = polyline_length_from_points(pts)
            else:
                w, h = cc.get_entity_bbox_size(ent)
                length = max(w or 0.0, h or 0.0)
        length = float(length or 0.0)
        is_arrow = cc.is_arrow(ent)
        if is_arrow:
            arrow_counts[dx] += 1
        lengths.append((length, dx, getattr(ent.dxf, 'handle', ''), is_arrow))

    # totals
    total_lines = counts['LINE']
    total_traces = counts['TRACE']
    total_arrows = sum(arrow_counts.values())

    lengths_sorted = sorted(lengths, key=lambda x: x[0])

    print(f"ARROW_MAX_SIZE = {cc.ARROW_MAX_SIZE}")
    print(f"Total LINE: {total_lines}")
    print(f"Total TRACE: {total_traces}")
    print(f"Total classified as arrows: {total_arrows}")
    print("")
    print("Top 20 menores comprimentos (length, dxftype, handle, is_arrow):")
    for item in lengths_sorted[:20]:
        print(item)

if __name__ == '__main__':
    if not os.path.exists(DXF_PATH):
        print('DXF not found:', DXF_PATH)
    else:
        analyze(DXF_PATH)
