import argparse
from er_diagram import ERDiagram, ERType
import yaml
import os


if __name__ == '__main__':
    with open('config_colors.yml') as f:
        colors = yaml.load(f, Loader=yaml.FullLoader)
        parser = argparse.ArgumentParser(description='Generate PDM')
        parser.add_argument('xlsx_file', help='Input excel file')
        parser.add_argument('-t', '--type', help='Type of diagram: physical, logical or conceptual default: physical', 
                            required=False, default='physical', choices=['physical', 'logical', 'conceptual'])
        parser.add_argument('-l', '--line-format', help='Line format: line or curve default: curve', default='curve', choices=['line', 'curve'])
        mapping_spline = {'line': 'polyline', 'curve': 'true'}
        args = parser.parse_args()
        erd = ERDiagram(colors)
        erd.import_from_xlsx(args.xlsx_file)
        graphviz_file = args.xlsx_file.replace('.xlsx', '.pdf')
        graphviz_file_name = os.path.basename(graphviz_file)
        graphviz_file = graphviz_file.replace(graphviz_file_name, f'{args.type.lower()}_{graphviz_file_name}')
        print(f'Generating {graphviz_file}')
        if args.type.upper() == 'CONCEPTUAL':
            engine = 'sfdp'
        else:
            engine = 'dot'
        erd.draw_pdf(graphviz_file, er_type=ERType[args.type.upper()], splines=mapping_spline[args.line_format.lower()], engine=engine)