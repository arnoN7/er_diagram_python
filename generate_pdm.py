import argparse
from er_diagram import ERDiagram, ERType
import yaml

if __name__ == '__main__':
    with open('config_colors.yml') as f:
        colors = yaml.load(f, Loader=yaml.FullLoader)
        parser = argparse.ArgumentParser(description='Generate PDM')
        parser.add_argument('xlsx_file', help='Input excel file')
        parser.add_argument('-t', '--type', help='Type of diagram: physical, logical or conceptual default: physical', 
                            required=False, default='physical', choices=['physical', 'logical', 'conceptual'])
        args = parser.parse_args()
        erd = ERDiagram(colors)
        erd.import_from_xlsx(args.xlsx_file)
        graphviz_file = args.xlsx_file.replace('.xlsx', '.pdf')
        erd.draw_pdf(graphviz_file, er_type=ERType[args.type.upper()])
