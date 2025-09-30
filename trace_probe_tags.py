import ezdxf
import os

PATH = r"c:\Users\matheusr\Documents\Layers_e_Cotas\ref\pilar treliçacdo.dxf"

def extract_vertices_from_tags(tags):
    # tags is an iterable of (code, value)
    coords = {}
    for code, value in tags:
        if code in (10,11,12,13, 20,21,22,23, 30,31,32,33):
            coords.setdefault(code, value)
    # reconstruct points: (10,20,30), (11,21,31), (12,22,32), (13,23,33)
    pts = []
    for i in range(10,14):
        x = coords.get(i)
        y = coords.get(i+10)
        z = coords.get(i+20)
        if x is not None and y is not None:
            pts.append((float(x), float(y), float(z) if z is not None else 0.0))
    return pts

if not os.path.exists(PATH):
    print('DXF not found', PATH)
    raise SystemExit(1)

doc = ezdxf.readfile(PATH)
msp = doc.modelspace()
count=0
for ent in msp:
    if ent.dxftype()!='TRACE':
        continue
    print('HANDLE', getattr(ent.dxf,'handle',''))
    try:
        tags = list(ent.tags)
        print('num tags', len(tags))
        # print first 20 tags
        print('first tags sample:', tags[:20])
        pts = extract_vertices_from_tags(tags)
        print('extracted pts:', pts)
    except Exception as e:
        print('error reading tags', e)
    print('-'*40)
    count+=1
    if count>=10:
        break
print('done')
