import ezdxf
from ezdxf import colors

def processar_dxf(arquivo_entrada, arquivo_saida, tolerancia=100):
    # Carregar o documento DXF
    doc = ezdxf.readfile(arquivo_entrada)
    msp = doc.modelspace()

    # Configurar layers fixos
    layers_fixos = {
        "EIXO": colors.YELLOW,
        "PERFIL": colors.RED,
    }

    # Criar/carregar layers fixos com cores específicas
    for nome, cor in layers_fixos.items():
        if nome not in doc.layers:
            layer = doc.layers.add(nome)
        else:
            layer = doc.layers.get(nome)
        layer.color = cor

    # Encontrar textos de referência (CHAPA "X")
    textos_chapa = []
    for entity in msp:
        if entity.dxftype() == 'TEXT':
            texto = entity.dxf.text.upper().strip()
            if texto.startswith(('CHAPA ', 'CHEPA ')):
                letra = texto.split()[-1].strip('"')
                textos_chapa.append((entity, letra))

    # Mover entidades para layers correspondentes
    for texto_entity, letra in textos_chapa:
        layer_nome = f'PEÇA {letra}'
        
        # Criar layer para a peça se não existir
        if layer_nome not in doc.layers:
            doc.layers.add(layer_nome)
        
        # Encontrar entidades próximas ao texto
        ponto_referencia = texto_entity.dxf.insert
        for entity in msp:
            if entity.dxftype() != 'TEXT':
                # Verificar proximidade baseada na bounding box
                if hasattr(entity, 'get_bbox'):
                    bbox = entity.get_bbox()
                    if bbox:
                        dist_x = max(bbox[0][0] - ponto_referencia[0], ponto_referencia[0] - bbox[1][0])
                        dist_y = max(bbox[0][1] - ponto_referencia[1], ponto_referencia[1] - bbox[1][1])
                        
                        if dist_x <= tolerancia and dist_y <= tolerancia:
                            entity.dxf.layer = layer_nome

    # Manter furação em vermelho (PERFIL)
    for entity in msp:
        if entity.dxftype() in ['CIRCLE', 'ARC']:  # Assumindo que furação são círculos/arcos
            entity.dxf.layer = "PERFIL"

    # Salvar arquivo modificado
    doc.saveas(arquivo_saida)

if __name__ == "__main__":
    processar_dxf("base.dxf", "saida.dxf")