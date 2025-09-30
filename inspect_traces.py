import ezdxf
import os
from ezdxf.math import BoundingBox

PATH = r"c:\Users\matheusr\Documents\Layers_e_Cotas\ref\pilar treliçacdo.dxf"

def safe_list(obj):
    try:
        return list(obj)
    except Exception as e:
        return f'<error: {e}>'

if not os.path.exists(PATH):
    print('DXF not found', PATH)
    raise SystemExit(1)

doc = ezdxf.readfile(PATH)
msp = doc.modelspace()
count = 0
for ent in msp:
    if ent.dxftype() != 'TRACE':
        continue
    print('HANDLE:', getattr(ent.dxf, 'handle', ''))
    print('DXFTYPE:', ent.dxftype())
    # attributes
    try:
        print('dxf attrs keys:', list(ent.dxf.attribs().keys()))
    except Exception as e:
        print('dxf attrs error:', e)
    # check methods
    print('has vertices_in_wcs:', hasattr(ent, 'vertices_in_wcs'))
    if hasattr(ent, 'vertices_in_wcs'):
        try:
            verts = safe_list(ent.vertices_in_wcs())
            print('vertices_in_wcs count:', len(verts) if isinstance(verts, list) else verts)
            if isinstance(verts, list) and verts:
                print('sample verts:', verts[:5])
        except Exception as e:
            print('vertices_in_wcs error:', e)
    print('has points:', hasattr(ent, 'points'))
    if hasattr(ent, 'points'):
        try:
            pts = safe_list(ent.points())
            print('points count:', len(pts) if isinstance(pts, list) else pts)
            if isinstance(pts, list) and pts:
                print('sample points:', pts[:5])
        except Exception as e:
            print('points error:', e)
    # bbox via BoundingBox
    try:
        verts_try = None
        try:
            verts_try = list(ent.vertices_in_wcs())
        except Exception:
            try:
                verts_try = list(ent.points())
            except Exception:
                verts_try = None
        print('verts_try:', type(verts_try), (len(verts_try) if isinstance(verts_try, list) else verts_try))
        if verts_try:
            xs = [v[0] for v in verts_try]
            ys = [v[1] for v in verts_try]
            print('bbox min/max:', min(xs), min(ys), max(xs), max(ys))
            bb = BoundingBox(verts_try)
            c = bb.center
            print('bbox center:', c.x, c.y)
    except Exception as e:
        print('bbox error:', e)
    print('-'*60)
    count += 1
    if count >= 30:
        break
print('done')
