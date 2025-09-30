import ezdxf
import os
import re
import math
from ezdxf.math import BoundingBox
from ezdxf import colors

# --- CONFIGURAÇÕES PRINCIPAIS ---
RAIO_DE_BUSCA = 800.0  # Ajuste conforme a escala desenho.
ARROW_MAX_SIZE = 4.0   # Tamanho máximo (unidades do desenho) para reconhecer uma entidade pequena como seta
ARROW_MAX_SIZE_ALT = 12.0  # Segundo limite maior usado com heurística de proporção
ARROW_ASPECT_RATIO = 4.0   # Proporção (maior/menor) mínima para considerar entidade longa e fina (seta)
ARROW_PROXIMITY = 20.0    # Distância máxima para considerar uma entidade próxima a uma dimensão (unidades do desenho)

# --- PALETA DE CORES E CAMADAS PADRÃO ---
CHAPA_COLORS = [6, 4, 3, 5, 230, 150] # Magenta, Ciano, Verde, Azul, Laranja, Roxo...

SEMANTIC_LAYERS = {
    "chumbador": ("CHUMBADORES", 1), # Vermelho
    "perfil":    ("PERFIS", 1),      # Vermelho
    "eixo":      ("EIXOS", 2),        # Amarelo
    #"0":        ("0", 2)          # Branco
    
}

COLOR_FURO = 1       # Vermelho
COLOR_LAYER_0 = 2    # Amarelo
COLOR_TEXTO_ALVO = 3 # Verde

PADROES_ALVO = [
    re.compile(r'CHAPA\s+"?([A-Z0-9]+)"?', re.IGNORECASE),
    re.compile(r'CH-([A-Z0-9]+)', re.IGNORECASE)
]

def get_aci_color_name(aci_index):
    color_map = {1: "Vermelho", 2: "Amarelo", 3: "Verde", 4: "Ciano", 5: "Azul", 6: "Magenta"}
    return color_map.get(aci_index, f"ACI {aci_index}")

def obter_centro_geometrico(entity):
    try:
        bbox = BoundingBox(entity.vertices_in_wcs())
        return bbox.center.xy
    except (AttributeError, TypeError, ValueError):
        try:
            if entity.dxftype() in ['CIRCLE', 'ARC']:
                return entity.dxf.center.xy
            if entity.dxftype() in ['TEXT', 'MTEXT', 'INSERT', 'ATTRIB']:
                return entity.dxf.insert.xy
        except AttributeError:
            return None
    return None

def get_entity_bbox_size(entity):
    """Retorna (width, height) do bounding box da entidade em WCS, ou (None, None) se inválido."""
    dx = None
    try:
        dx = entity.dxftype()
    except Exception:
        dx = None

    # LINE: usar start/end se disponível
    if dx == 'LINE':
        try:
            s = entity.dxf.start
            e = entity.dxf.end
            xs = [s[0], e[0]]
            ys = [s[1], e[1]]
            width = max(xs) - min(xs)
            height = max(ys) - min(ys)
            return (abs(width), abs(height))
        except Exception:
            pass

    # TRACE: tenta obter pontos através de vários métodos
    if dx == 'TRACE' or dx == 'POLYLINE' or dx == 'LWPOLYLINE':
        # 1) vertices_in_wcs
        try:
            verts = entity.vertices_in_wcs()
            xs = [v[0] for v in verts]
            ys = [v[1] for v in verts]
            if xs and ys:
                width = max(xs) - min(xs)
                height = max(ys) - min(ys)
                return (abs(width), abs(height))
        except Exception:
            pass
        # 2) points() method
        try:
            pts = list(entity.points())
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if xs and ys:
                width = max(xs) - min(xs)
                height = max(ys) - min(ys)
                return (abs(width), abs(height))
        except Exception:
            pass

    # Fallback geral: vertices_in_wcs for other entity types
    try:
        verts = entity.vertices_in_wcs()
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        if not xs or not ys:
            return (None, None)
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        return (abs(width), abs(height))
    except Exception:
        pass

    # CIRCLE/ARC fallback
    try:
        if dx in ['CIRCLE', 'ARC']:
            r = float(entity.dxf.radius)
            return (2*r, 2*r)
    except Exception:
        pass

    return (None, None)

def is_arrow(entity):
    """Heurística simples para detectar setas/arrowheads: geometria curta/pequena.

    Usa o tamanho do bounding box; se a maior dimensão for menor que ARROW_MAX_SIZE
    considera-se uma seta e, portanto, não deve ser movida para a layer da peça.
    """
    try:
        dx = entity.dxftype()
    except Exception:
        return False
    # Tipos que frequentemente representam setas: LINE, TRACE, LWPOLYLINE, POLYLINE
    if dx not in ('LINE', 'TRACE', 'LWPOLYLINE', 'POLYLINE'):
        return False
    w, h = get_entity_bbox_size(entity)
    if w is None or h is None:
        return False
    maxdim = max(w, h)
    mindim = min(w, h) if min(w, h) > 0 else 0.0
    # Caso 1: muito pequeno -> seta
    if maxdim <= ARROW_MAX_SIZE:
        return True
    # Caso 2: se menor que ALT e aspecto alto (longo e fino) -> seta
    if maxdim <= ARROW_MAX_SIZE_ALT and mindim > 0:
        aspect = maxdim / mindim
        if aspect >= ARROW_ASPECT_RATIO:
            return True
    return False

def ensure_layer(doc, layer_name, color):
    if layer_name not in doc.layers:
        print(f"  + Criando camada '{layer_name}' com a cor {get_aci_color_name(color)}.")
        doc.layers.new(name=layer_name, dxfattribs={'color': color})
    else:
        doc.layers.get(layer_name).dxf.color = color

def set_layer0_to_yellow(doc):
    """Define a cor da camada '0' para amarelo (valor ACI definido em COLOR_LAYER_0).

    Se a camada '0' não existir (caso raro), ela será criada com a cor especificada.
    """
    layer_name = '0'
    try:
        if layer_name not in doc.layers:
            print(f"  + Criando camada '{layer_name}' com a cor {get_aci_color_name(COLOR_LAYER_0)}.")
            doc.layers.new(name=layer_name, dxfattribs={'color': COLOR_LAYER_0})
        else:
            # Atualiza o atributo de cor da camada '0'
            doc.layers.get(layer_name).dxf.color = COLOR_LAYER_0
            print(f"  * Camada '{layer_name}' atualizada para cor {get_aci_color_name(COLOR_LAYER_0)}.")
    except Exception as e:
        print(f"Aviso: não foi possível ajustar a cor da camada '0': {e}")

def process_cotas_and_texts(doc, msp, processed_handles):
    """Move DIMENSION (cotas rotacionadas incluídas) para 'COTAS' e MTEXT para 'TEXTO'.

    - Cria camadas 'COTAS' (amarelo) e 'TEXTO' (verde) se não existirem.
    - Move todas as entidades dxftype 'DIMENSION' para 'COTAS' e pinta amarelo.
    - Move todas as entidades dxftype 'MTEXT' para 'TEXTO' e pinta verde.
    - Marca os handles afetados em processed_handles.
    """
    cotas_layer = 'COTAS'
    texto_layer = 'TEXTO'
    ensure_layer(doc, cotas_layer, COLOR_LAYER_0)
    ensure_layer(doc, texto_layer, COLOR_TEXTO_ALVO)

    dimension_centers = []
    for ent in msp:
        try:
            dx = ent.dxftype()
        except Exception:
            continue
        if dx == 'DIMENSION':
            try:
                ent.dxf.layer = cotas_layer
                ent.dxf.color = COLOR_LAYER_0
                processed_handles.add(ent.dxf.handle)
                # try to record center of dimension
                try:
                    c = obter_centro_geometrico(ent)
                    if c:
                        dimension_centers.append(c)
                except Exception:
                    pass
            except Exception:
                pass
        elif dx == 'MTEXT':
            try:
                ent.dxf.layer = texto_layer
                ent.dxf.color = COLOR_TEXTO_ALVO
                processed_handles.add(ent.dxf.handle)
            except Exception:
                pass
    return dimension_centers

def is_near_dimension(entity, dimension_centers):
    try:
        c = obter_centro_geometrico(entity)
        if not c:
            return False
        for dc in dimension_centers:
            if dc and math.dist(c, dc) <= ARROW_PROXIMITY:
                return True
    except Exception:
        return False
    return False

def collect_dimension_centers(msp):
    """Scan modelspace for DIMENSION entities and return their centres (without moving them)."""
    centers = []
    for ent in msp:
        try:
            if ent.dxftype() == 'DIMENSION':
                c = obter_centro_geometrico(ent)
                if c:
                    centers.append(c)
        except Exception:
            continue
    return centers

def move_nearby_unclosed_lines_to_setas(doc, msp, alvos_chapa, processed_handles, arrow_proximity=ARROW_PROXIMITY, raio_de_busca=RAIO_DE_BUSCA, moved_setas_list=None):
    """Move linhas/trace não fechadas próximas às CHAPAs para a layer 'SETAS'.

    - alvos_chapa: dict(nome_peca -> list de localizações)
    - Usa RAIO_DE_BUSCA para proximidade e pinta como COLOR_LAYER_0 (amarelo)
    - Marca handles em processed_handles para evitar reprocessamento
    """
    setas_layer = 'SETAS'
    ensure_layer(doc, setas_layer, COLOR_LAYER_0)
    # Criar lista de centros por chapa para busca rápida
    chapa_centers = []
    for nome, locs in alvos_chapa.items():
        for loc in locs:
            if loc:
                chapa_centers.append((nome, loc))

    for entity in msp:
        try:
            if entity.dxf.handle in processed_handles:
                continue
        except Exception:
            pass
        dx = None
        try:
            dx = entity.dxftype()
        except Exception:
            continue
        # Tipos candidatos: LINE, TRACE, LWPOLYLINE, POLYLINE
        if dx not in ('LINE', 'TRACE', 'LWPOLYLINE', 'POLYLINE'):
            continue
        # Polylines podem ser fechadas; IGNORAR se fechada
        is_closed = False
        try:
            # Alguns objetos expõem is_closed
            is_closed = getattr(entity, 'is_closed', False)
        except Exception:
            is_closed = False
        if is_closed:
            continue

        # Centro/posição da entidade
        centro = obter_centro_geometrico(entity)
        if not centro:
            # fallback para tentar bbox
            w, h = get_entity_bbox_size(entity)
            if w is None or h is None:
                continue
            # build center from bbox
            try:
                verts = entity.vertices_in_wcs()
                xs = [v[0] for v in verts]
                ys = [v[1] for v in verts]
                centro = ((max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0)
            except Exception:
                continue

        # verificar proximidade com qualquer centro de chapa
        near_chapa = False
        for nome, chapa_loc in chapa_centers:
            try:
                if math.dist(centro, chapa_loc) <= RAIO_DE_BUSCA:
                    near_chapa = True
                    break
            except Exception:
                continue
        if near_chapa:
            try:
                try:
                    orig_layer = getattr(entity.dxf, 'layer', None)
                except Exception:
                    orig_layer = None
                entity.dxf.layer = setas_layer
                entity.dxf.color = COLOR_LAYER_0
                processed_handles.add(entity.dxf.handle)
                if moved_setas_list is not None:
                    # If caller provided a list for details, append a dict; otherwise append the handle
                    try:
                        # check if list already contains dicts or is empty -> append dict
                        if not moved_setas_list or isinstance(moved_setas_list[0], dict):
                            moved_setas_list.append({'handle': entity.dxf.handle, 'layer': setas_layer, 'original_layer': orig_layer})
                        else:
                            moved_setas_list.append(entity.dxf.handle)
                    except Exception:
                        try:
                            moved_setas_list.append(entity.dxf.handle)
                        except Exception:
                            pass
                    # if list of details expected, support dict entries
                    try:
                        if isinstance(moved_setas_list, list) and (len(moved_setas_list) == 0 or isinstance(moved_setas_list[0], dict) == False):
                            # already appending handles only; skip adding details
                            pass
                    except Exception:
                        pass
            except Exception:
                pass

def reestruturar_desenho_final(input_path: str, output_path: str, *, protect_by_dimension=False, arrow_proximity=None, raio_de_busca=None):
    try:
        doc = ezdxf.readfile(input_path)
        msp = doc.modelspace()
    except Exception as e:
        print(f"Erro crítico ao ler o arquivo: {e}")
        return

    print("Iniciando reestruturação com hierarquia profissional.")
    set_layer0_to_yellow(doc)
    processed_handles = set()
    moved_setas = []
    moved_setas_details = []
    moved_chapas = {}
    moved_chapas_details = {}

    # allow overrides from caller
    if arrow_proximity is None:
        arrow_proximity = ARROW_PROXIMITY
    if raio_de_busca is None:
        raio_de_busca = RAIO_DE_BUSCA

    # --- FASE 1: SEMÂNTICA ---
    print("\n--- Fase 1: Identificando sistemas (Perfis, Chumbadores, Eixos) ---")
    for keyword, (layer_name, color) in SEMANTIC_LAYERS.items():
        ensure_layer(doc, layer_name, color)

    for entity in msp:
        original_layer = entity.dxf.layer.lower()
        eh_tracejado = hasattr(entity.dxf, 'linetype') and entity.dxf.linetype.lower() not in ['continuous', 'byblock', 'bylayer']

        for keyword, (target_layer, _) in SEMANTIC_LAYERS.items():
            if (keyword == 'eixo' and eh_tracejado) or keyword in original_layer:
                entity.dxf.layer = target_layer
                entity.dxf.color = 256 # BYLAYER
                processed_handles.add(entity.dxf.handle)
                break

    # If requested, collect dimension centers early
    dimension_centers = []
    if protect_by_dimension:
        dimension_centers = collect_dimension_centers(msp)

    # --- FASE 2: AGRUPAMENTO DAS CHAPAS ---
    print("\n--- Fase 2: Mapeando e agrupando Chapas ---")
    alvos_chapa = {}
    for entity in msp.query('TEXT MTEXT ATTRIB'):
        text_content = ""
        if entity.dxftype() in ('TEXT', 'ATTRIB'):
            text_content = entity.dxf.text
        elif entity.dxftype() == 'MTEXT':
            text_content = entity.plain_text()
        for padrao in PADROES_ALVO:
            match = padrao.search(text_content)
            if match:
                nome_peca = match.group(1).upper()
                if nome_peca not in alvos_chapa:
                    alvos_chapa[nome_peca] = []
                alvos_chapa[nome_peca].append(obter_centro_geometrico(entity))
                entity.dxf.color = COLOR_TEXTO_ALVO
                processed_handles.add(entity.dxf.handle)
                break

    color_index = 0
    for nome_peca, localizacoes in alvos_chapa.items():
        novo_layer_name = f"CHAPA {nome_peca}"
        cor_da_chapa = CHAPA_COLORS[color_index % len(CHAPA_COLORS)]
        ensure_layer(doc, novo_layer_name, cor_da_chapa)
        color_index += 1

        for entity in msp:
            if entity.dxf.handle in processed_handles:
                continue
            loc_entidade = obter_centro_geometrico(entity)
            if not loc_entidade:
                continue
            # Check if entity is closed (e.g., a plate boundary). If closed, consider it CHAPA geometry.
            is_closed = False
            try:
                is_closed = bool(getattr(entity, 'is_closed', False))
            except Exception:
                is_closed = False
            # If entity is not closed and it's on layer '0', keep it yellow and do not move to CHAPA
            try:
                orig_layer = entity.dxf.layer.lower()
            except Exception:
                orig_layer = ''
            if not is_closed and orig_layer == '0':
                try:
                    entity.dxf.color = COLOR_LAYER_0
                except Exception:
                    pass
                continue
            for loc_alvo in localizacoes:
                if loc_alvo and math.dist(loc_entidade, loc_alvo) <= raio_de_busca:
                    # If the entity is line-like and very near the chapa target (likely part of an arrow line),
                    # move it to 'SETAS' and do NOT count it as part of the CHAPA layer.
                    try:
                        ent_type = entity.dxftype()
                    except Exception:
                        ent_type = None
                    if ent_type in ('LINE', 'TRACE', 'LWPOLYLINE', 'POLYLINE'):
                        try:
                            if not getattr(entity, 'is_closed', False) and math.dist(loc_entidade, loc_alvo) <= arrow_proximity:
                                ensure_layer(doc, 'SETAS', COLOR_LAYER_0)
                                try:
                                    orig_layer = getattr(entity.dxf, 'layer', None)
                                    entity.dxf.layer = 'SETAS'
                                    entity.dxf.color = COLOR_LAYER_0
                                    processed_handles.add(entity.dxf.handle)
                                    moved_setas.append(entity.dxf.handle)
                                    moved_setas_details.append({'handle': entity.dxf.handle, 'layer': 'SETAS', 'original_layer': orig_layer})
                                except Exception:
                                    pass
                                break
                        except Exception:
                            pass
                    # Se a entidade for uma seta (heurística), mantemos amarela e NÃO movemos para a layer da chapa
                    if is_arrow(entity):
                        try:
                            entity.dxf.color = COLOR_LAYER_0
                        except Exception:
                            pass
                        # não marca como processed_handles para que outros passos possam considerar se necessário
                        break
                    # Caso contrário, move a entidade para a layer da CHAPA
                    try:
                        orig_layer = getattr(entity.dxf, 'layer', None)
                    except Exception:
                        orig_layer = None
                    entity.dxf.layer = novo_layer_name
                    entity.dxf.color = 256 # BYLAYER
                    processed_handles.add(entity.dxf.handle)
                    moved_chapas.setdefault(novo_layer_name, []).append(entity.dxf.handle)
                    moved_chapas_details.setdefault(novo_layer_name, []).append({'handle': entity.dxf.handle, 'layer': novo_layer_name, 'original_layer': orig_layer})
                    break

    # After grouping CHAPAs, move nearby unclosed line-like entities into 'SETAS'
    move_nearby_unclosed_lines_to_setas(doc, msp, alvos_chapa, processed_handles, arrow_proximity=arrow_proximity, raio_de_busca=raio_de_busca, moved_setas_list=moved_setas)

    # Also, if protect_by_dimension, move entities near dimension_centers to SETAS
    if protect_by_dimension and dimension_centers:
        for entity in msp:
            try:
                if entity.dxf.handle in processed_handles:
                    continue
            except Exception:
                pass
            try:
                if is_near_dimension(entity, dimension_centers):
                    ensure_layer(doc, 'SETAS', COLOR_LAYER_0)
                    try:
                        orig_layer = getattr(entity.dxf, 'layer', None)
                    except Exception:
                        orig_layer = None
                    try:
                        entity.dxf.layer = 'SETAS'
                        entity.dxf.color = COLOR_LAYER_0
                        processed_handles.add(entity.dxf.handle)
                        moved_setas.append(entity.dxf.handle)
                        moved_setas_details.append({'handle': entity.dxf.handle, 'layer': 'SETAS', 'original_layer': orig_layer})
                    except Exception:
                        pass
            except Exception:
                pass

    # Tratar cotas rotacionadas (DIMENSION) e MTEXT agora
    dimension_centers = process_cotas_and_texts(doc, msp, processed_handles)

    # --- FASE 3: FUROS E LIMPEZA ---
    print("\n--- Fase 3: Aplicando overrides (Furos) e limpando ---")
    for entity in msp:
        dxftype = entity.dxftype()
        # Mover HATCH para camada própria e pintar vermelho
        if dxftype == 'HATCH':
            try:
                ensure_layer(doc, 'HATCHES', COLOR_FURO)
                entity.dxf.layer = 'HATCHES'
                entity.dxf.color = COLOR_FURO
                processed_handles.add(entity.dxf.handle)
            except Exception:
                pass
            continue
        eh_furo = (
            dxftype == 'CIRCLE' or 
            dxftype == 'TRACE' or
            (dxftype in ['LWPOLYLINE', 'POLYLINE'] and getattr(entity, 'is_closed', False))
        )
        if eh_furo:
            entity.dxf.color = COLOR_FURO
        elif entity.dxf.handle not in processed_handles and entity.dxf.layer.lower() == '0':
            entity.dxf.color = COLOR_LAYER_0

    print("\n" + "="*50)
    print("Reestruturação concluída!")
    try:
        doc.saveas(output_path)
        print(f"O novo arquivo foi salvo em: '{os.path.abspath(output_path)}'")
    except IOError as e:
        print(f"Erro ao salvar o arquivo: {e}")
    print("="*50)

    # --- RELATÓRIO: contagens por camada ---
    layer_counts = {}
    for ent in msp:
        try:
            layer = ent.dxf.layer
        except Exception:
            layer = '<unknown>'
        layer_counts[layer] = layer_counts.get(layer, 0) + 1

    report_path = os.path.splitext(output_path)[0] + '_report.txt'
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('Relatório de contagens por camada\n')
            f.write(f'Arquivo processado: {os.path.basename(output_path)}\n')
            f.write('---\n')
            total = 0
            for layer_name, count in sorted(layer_counts.items()):
                f.write(f"{layer_name}: {count}\n")
                total += count
            f.write('---\n')
            f.write(f'Total de entidades: {total}\n')
            f.write(f'Entidades marcadas como processadas (handles): {len(processed_handles)}\n')
        print(f"Relatório de contagem por camada salvo em: '{os.path.abspath(report_path)}'")
    except Exception as e:
        print(f"Erro ao gravar relatório: {e}")

    # write handles report
    handles_report_path = os.path.splitext(output_path)[0] + '_handles_report.txt'
    handles_csv_path = os.path.splitext(output_path)[0] + '_handles_report.csv'
    try:
        with open(handles_report_path, 'w', encoding='utf-8') as hf:
            hf.write('Handles moved to SETAS:\n')
            for h in moved_setas:
                hf.write(f"{h}\n")
            hf.write('\nHandles moved to CHAPAs:\n')
            for layer_name, handles in moved_chapas.items():
                hf.write(f"# {layer_name}\n")
                for h in handles:
                    hf.write(f"{h}\n")
        print(f"Handles report saved in: '{os.path.abspath(handles_report_path)}'")
    except Exception as e:
        print(f"Erro ao gravar handles report: {e}")
    try:
        # write CSV: layer,handle,original_layer
        with open(handles_csv_path, 'w', encoding='utf-8') as cf:
            cf.write('layer,handle,original_layer\n')
            # setas details
            for d in moved_setas_details:
                cf.write(f"{d.get('layer')},{d.get('handle')},{d.get('original_layer')}\n")
            # chapas details
            for layer_name, details in moved_chapas_details.items():
                for d in details:
                    cf.write(f"{d.get('layer')},{d.get('handle')},{d.get('original_layer')}\n")
        print(f"Handles CSV saved in: '{os.path.abspath(handles_csv_path)}'")
    except Exception as e:
        print(f"Erro ao gravar handles CSV: {e}")

    # return summary dict for programmatic use
    summary = {
        'output_path': os.path.abspath(output_path),
        'report_path': os.path.abspath(report_path),
        'handles_report_path': os.path.abspath(handles_report_path),
        'moved_setas': list(moved_setas),
        'moved_chapas': {k: list(v) for k, v in moved_chapas.items()},
        'processed_handles_count': len(processed_handles),
        'layer_counts': layer_counts,
    }
    return summary



def main():
    print("--------------------------------------------------")
    print("  Reestruturador Profissional de Desenhos CAD v3  ")
    print("--------------------------------------------------")
    input_file = input("Caminho do arquivo DXF de entrada: ")
    if not os.path.exists(input_file):
        print("Erro: Arquivo não encontrado.")
        return
    base, ext = os.path.splitext(input_file)
    output_file = input(f"Caminho de saída (Enter para '{base}_pro_v3{ext}'): ") or f"{base}_pro_v3{ext}"
    reestruturar_desenho_final(input_file, output_file)

if __name__ == "__main__":
    main()
