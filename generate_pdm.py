import csv
import pandas as pd
import graphviz
from jinja2 import Environment, FileSystemLoader


# Generate PDM from the an xls file or a csv file

class Relation:
    class RelationErr(Exception):
        pass
    def __init__(self, tablepk:str, tablefk:str, cardinality:str='1:1', fk:str=""):
        self.table1 = tablepk
        self.table2 = tablefk
        self.cardinality = cardinality
        self.fk = fk
    def __str__(self):
        return f'{self.table1} -> {self.table2}, {self.cardinality}, {self.fk}'

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
    class FKErr(Exception):
        pass
    def __init__(self, table_name:str, name:str, type:str, fk:str, nullable:bool=True):
        super().__init__(table_name, name, type, nullable)
        self.columnfk = self.columnpk = name
        self.table_pk = None
        self.cardinality = None
        if not str(fk):
            print(f'ERROR: incorrect FK format {fk}')
            raise ColumnFK.FKErr
        try:
            fk_key, self.table_pk, self.cardinality = str(fk).split(' ')
            if '.' in self.table_pk:
                self.table_pk, self.columnpk = self.table_pk.split('.')
            if not fk_key == 'FK':
                print(f'ERROR: incorrect FK format {fk}')
                raise ColumnFK.FKErr
        except:
            print(f'ERROR: incorrect FK format {fk}')
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
    def __init__(self, name:str, columnsPK:list[ColumnPK], columnsFK:list[ColumnFK], columnsArgs:list[ColumnArg], relations={}):
        self.name = name
        self.columnsPK = columnsPK
        self.columnsFK = columnsFK
        self.columnsArgs = columnsArgs
        self.relations = relations
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

def get_html_table(table:Table):
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("html_table_template.html")
    content = template.render(table=table)
    with open(f"debug/{table.name}.html", mode="w", encoding="utf-8") as message:
        message.write(content)
    return content

xls = pd.ExcelFile('sample_datamodel.xlsx')
tables = filter(is_table_sheet, xls.sheet_names)

model = []
for table_sheet in tables:
    df = pd.read_excel(xls, table_sheet)
    column_list_pk = df.loc[df['pk'].notnull(), ['name', 'type', 'nullable']].to_dict('records')
    columns_pk = [ColumnPK(get_table_name(table_sheet), **column) for column in column_list_pk]
    column_list_fk = df.loc[df['fk'].notnull(), ['name', 'type', 'fk', 'nullable']].to_dict('records')
    columns_fk = [ColumnFK(get_table_name(table_sheet), **column) for column in column_list_fk] 
    columns_args = df.loc[df['pk'].isnull() & df['fk'].isnull(), ['name', 'type', 'nullable']].to_dict('records')
    columns_args = [ColumnArg(get_table_name(table_sheet), **column) for column in columns_args]

    relations = {}
    for column in columns_fk:
        if column.table_pk in relations:
            if relations[column.table_pk].cardinality == column.cardinality:
                relations[column.table_pk].fk += f', {column.columnfk}'
            else:
                print(f'ERROR: Cardinality mismatch between {column.table_name} -> {column.table_pk} previous: {relations[column.table_pk].cardinality} current: {column.cardinality}')
                raise Relation.RelationErr
        else:
            relations[column.table_pk] = Relation(column.table_name, column.table_pk, column.cardinality, column.columnfk)
    table = Table(get_table_name(table_sheet), columns_pk, columns_fk, columns_args, relations)
    model.append(table)

model_graph = graphviz.Digraph('Database', filename='database.gv', graph_attr={'concentrate': 'true'})
for table in model:
    table_struct = get_html_table(table)
    model_graph.node(table.name, label=table_struct, shape='none')

for table in model:
    for fk in table.columnsFK:
        model_graph.edge(f'{table.name}:{fk.name}', f'{fk.table_pk}:{fk.columnpk}')
model_graph.render(view=True)