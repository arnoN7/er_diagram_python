import csv
import pandas as pd
import graphviz
from jinja2 import Environment, FileSystemLoader
from enum import Enum
import yaml

# Generate PDM from the an xls file or a csv file

class ERType(Enum):
    PHYSICAL = 1
    LOGICAL = 2
    CONCEPTUAL = 3

class Column:
    def __init__(self, table_name:str, name:str, type:str, nullable:bool=True):
        self.name = name
        self.type = type
        self.nullable = nullable
        self.table_name = table_name
        self.fk = None
            
    def __str__(self):
        return f'{self.name} {self.type} nullable:{self.nullable}'

class ColumnArg(Column):
    pass

class ColumnFK(Column):
    mapping_cardinality = {
        '0': 'none',
        '1': 'tee',
        'n': 'crow'
    }
    class FKErr(Exception):
        pass
    def __init__(self, table_name:str, name:str, type:str, fk:str, nullable:bool=True):
        super().__init__(table_name, name, type, nullable)
        self.columnfk = self.columnpk = name
        self.table_pk = None
        cardinality = None
        self.cardinality = '0'
        self.cardinalityFK = '0'
        error_msg = f'ERROR: incorrect FK format "{fk}" in table {table_name} must be FK <fk_table>.<column> <cardinality>:<cardinality_fk>'
        try:
            fk_key, self.table_pk, cardinality = str(fk).split(' ')
            if '.' in self.table_pk:
                self.table_pk, self.columnpk = self.table_pk.split('.')
            if ':' in cardinality:
                self.cardinality = cardinality.split(':')[0]
                self.cardinalityFK = cardinality.split(':')[1]
            else:
                raise ColumnFK.FKErr
            if not fk_key == 'FK':
                print(error_msg)
                raise ColumnFK.FKErr
        except:
            print(error_msg)
            raise ColumnFK.FKErr 
    def getarrowhead(self):
        try:
            return ColumnFK.mapping_cardinality[self.cardinalityFK]
        except:
            print(f'ERROR: incorrect cardinality {self.cardinalityFK} must be 0, 1 or n')
            raise ColumnFK.FKErr
    def getarrowtail(self):
        try:
            return ColumnFK.mapping_cardinality[self.cardinality]
        except:
            print(f'ERROR: incorrect cardinality {self.cardinality} must be 0, 1 or n')
            raise ColumnFK.FKErr

class ColumnPK(Column):
    class PKErr(Exception):
        pass
    def __init__(self, table_name:str, name:str, type:str, nullable:bool=False):
        if nullable:
            print(f'ERROR: PK column {name} is nullable')
            raise ColumnPK.PKErr
        super().__init__(table_name, name, type, nullable)
        self.pk = True



class Table:
    def __init__(self, name:str, columnsPK:list[ColumnPK], columnsFK:list[ColumnFK], columnsArgs:list[ColumnArg]):
        self.name = name
        self.columnsPK = columnsPK
        self.columnsFK = columnsFK
        self.columnsArgs = columnsArgs
    def __str__(self):
        columns = '\n'.join([f'\t{column}' for column in self.columns])
        return f'{self.name} {{\n{columns}\n}}'

def is_table_sheet(sheet_name:str):
    return 'table ' in sheet_name.lower()

def get_table_name(sheet_name:str):
    return sheet_name.split('table ')[-1]

def read_csv(file_path:str):
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        return list(reader)

def get_html_table(table:Table, colors:dict, er_type:ERType=ERType.PHYSICAL):
    if er_type == ERType.CONCEPTUAL:
        return table.name
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("html_table_template.html")
    content = template.render(table=table, er_type=er_type.value, colors=colors)
    with open(f"debug/{table.name}.html", mode="w", encoding="utf-8") as message:
        message.write(content)
    return content

def get_shape(er_type:ERType):
    if er_type == ERType.PHYSICAL:
        return 'none'
    elif er_type == ERType.LOGICAL:
        return 'none'
    elif er_type == ERType.CONCEPTUAL:
        return 'box'
    else:
        print(f'ERROR: incorrect ER type {er_type}')
        raise ValueError(f'incorrect ER type {er_type}')


def generate_diagram(file:str, colors:dict, er_type:ERType=ERType.PHYSICAL):
    try:
        xls = pd.ExcelFile(file)
        tables = filter(is_table_sheet, xls.sheet_names)
        model:list[Table] = []
        for table_sheet in tables:
            df = pd.read_excel(xls, table_sheet)
            column_list_pk = df.loc[df['pk'].notnull(), ['name', 'type', 'nullable']].to_dict('records')
            columns_pk = [ColumnPK(get_table_name(table_sheet), **column) for column in column_list_pk]
            column_list_fk = df.loc[df['fk'].astype(str).str.startswith("FK "), ['name', 'type', 'fk', 'nullable']].to_dict('records')
            columns_fk = [ColumnFK(get_table_name(table_sheet), **column) for column in column_list_fk] 
            columns_args = df.loc[df['pk'].isnull() & df['fk'].isnull(), ['name', 'type', 'nullable']].to_dict('records')
            columns_args = [ColumnArg(get_table_name(table_sheet), **column) for column in columns_args]

            table = Table(get_table_name(table_sheet), columns_pk, columns_fk, columns_args)
            model.append(table)
        pdf_name = f'{file.replace(".xlsx","")}'
        model_graph = graphviz.Digraph('Database', filename=pdf_name, graph_attr={'concentrate': 'true', 'rankdir': 'LR'})
        for table in model:
            table_struct = get_html_table(table, colors, er_type)
            if er_type == ERType.CONCEPTUAL:
                model_graph.node(table.name, fillcolor=colors['BG_COLOR'], style='filled', shape=get_shape(er_type), fontcolor=colors['DARK_COLOR'])
            else:
                model_graph.node(table.name, label=table_struct, shape=get_shape(er_type))

        for table in model:
            for fk in table.columnsFK:
                model_graph.edge(f'{table.name}:{fk.name}', f'{fk.table_pk}:{fk.columnpk}',arrowhead=fk.getarrowhead(), 
                                arrowtail=fk.getarrowtail(), dir='both', color=colors['DARK_COLOR'])
        model_graph.render(view=True)
    except Exception as e:
        print
        pass

if __name__ == '__main__':
    #read colors from yaml file
    with open('colors.yml') as f:
        colors = yaml.load(f, Loader=yaml.FullLoader)
        generate_diagram('example/sample_datamodel.xlsx', colors, er_type=ERType.LOGICAL)