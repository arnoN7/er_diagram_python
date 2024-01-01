import argparse
from er_diagram import ERDiagram, ERType
import yaml

if __name__ == '__main__':
    with open('config_colors.yml') as f:
        colors = yaml.load(f, Loader=yaml.FullLoader)
        parser = argparse.ArgumentParser(description='Generate PDM')
        parser.add_argument('file', help='Input file')
        parser.add_argument('-t', '--type', help='Type of diagram: physical, logical or conceptual default: physical', 
                            default='physical', choices=['physical', 'logical', 'conceptual'])
        args = parser.parse_args()
        erd = ERDiagram(colors)
        erd.import_from_xlsx(args.file)
        graphviz_file = args.file.replace('.xlsx', '.pdf')
        erd.draw_pdf(graphviz_file, er_type=ERType[args.type.upper()])
