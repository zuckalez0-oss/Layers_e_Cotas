from color_change2 import reestruturar_desenho_final
import os

base = r'c:\Users\matheusr\Documents\Layers_e_Cotas\ref\pilar treliçacdo.dxf'
out1 = r'c:\Users\matheusr\Documents\Layers_e_Cotas\ref\pilar_t_out1.dxf'
out2 = r'c:\Users\matheusr\Documents\Layers_e_Cotas\ref\pilar_t_out2.dxf'

print('Running 1...')
res1 = reestruturar_desenho_final(base, out1, protect_by_dimension=True, arrow_proximity=20.0, raio_de_busca=800.0)
print('Running 2...')
res2 = reestruturar_desenho_final(base, out2, protect_by_dimension=True, arrow_proximity=20.0, raio_de_busca=800.0)

print('res1 handles csv:', res1.get('handles_report_path'))
print('res2 handles csv:', res2.get('handles_report_path'))
