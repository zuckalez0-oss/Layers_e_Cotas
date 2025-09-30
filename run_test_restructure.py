from color_change2 import reestruturar_desenho_final
import os

input_path = r"c:\Users\matheusr\Documents\Layers_e_Cotas\ref\pilar treliçacdo.dxf"
base, ext = os.path.splitext(input_path)
output_path = base + "_test_out" + ext
print('Input:', input_path)
print('Output:', output_path)
reestruturar_desenho_final(input_path, output_path)
print('Done')
