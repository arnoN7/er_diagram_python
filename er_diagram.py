import csv
import pandas as pd
import graphviz
from jinja2 import Environment, FileSystemLoader
from enum import Enum
import yaml
import os


# Generate PDM from the an xls file or a csv file

class ERType(Enum):
    PHYSICAL = 1
    LOGICAL = 2
    CONCEPTUAL = 3

class Column:
    class HiddenState(Enum):
        HIDDEN = 1
        HIDDEN_IN_LOGICAL = 2
        VISIBLE = 3
    
    def __init__(self, table_name:str, name:str, type:str):
        self.name = name
        self.hidden = Column.HiddenState.VISIBLE
        if ':' in name:
            self.name, hidden = name.split(':')
            if hidden.upper() == 'H':
                self.hidden = Column.HiddenState.HIDDEN
            else:
                self.hidden = Column.HiddenState.HIDDEN_IN_LOGICAL 
        self.type = type
        self.table_name = table_name
        self.fk = None
        self.pk = False
            
    def __str__(self):
        return f'{self.name} {self.type}'
    
    def is_hidden(self, ERType:ERType=ERType.PHYSICAL):
        if ERType == ERType.PHYSICAL:
            return self.hidden == Column.HiddenState.HIDDEN
        elif ERType == ERType.LOGICAL:
            return self.hidden == Column.HiddenState.HIDDEN_IN_LOGICAL or self.hidden == Column.HiddenState.HIDDEN
        else:
            return False

class ColumnArg(Column):
    pass

class ColumnFK(Column):
    mapping_cardinality = {
        '1': 'tee',
        'n': 'crow',
        '11' : 'teetee',
        '01' : 'teeodot',
        '0n' : 'crowodot',
        '1n' : 'crowtee'       
    }
    class FKErr(Exception):
        pass
    def __init__(self, table_name:str, name:str, type:str, fk:str):
        super().__init__(table_name, name, type)
        if not fk:
            return
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
                self.cardinality = cardinality.split(':')[0].lower()
                self.cardinalityFK = cardinality.split(':')[1].lower()
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
            print(f'ERROR: incorrect cardinality {self.cardinalityFK} must be 0, 1 or n in {self.table_name}.{self.name}')
            raise ColumnFK.FKErr
    def getarrowtail(self):
        try:
            return ColumnFK.mapping_cardinality[self.cardinality]
        except:
            print(f'ERROR: incorrect cardinality {self.cardinality} must be 0, 1 or n in {self.table_name}.{self.name}')
            raise ColumnFK.FKErr

class ColumnPK(ColumnFK):
    class PKErr(Exception):
        pass
    def __init__(self, table_name:str, name:str, type:str, fk:str=None):
        super().__init__(table_name, name, type, fk)
        self.pk = True
    
    def is_fk(self):
        return hasattr(self, 'table_pk')



class Table:
    def __init__(self, name:str, columnsPK:list[ColumnPK], columnsFK:list[ColumnFK], columnsArgs:list[ColumnArg], type:str='table'):
        self.name = name
        self.columnsPK = columnsPK
        self.columnsFK = columnsFK
        self.columnsArgs = columnsArgs
        self.type = type
    def __str__(self):
        columns = '\n'.join([f'\t{column}' for column in self.columns])
        return f'{self.name} {{\n{columns}\n}}'
    
    def get_columns(self, type:str, er_type:ERType=ERType.PHYSICAL):
            return [column for column in getattr(self, type) if not column.is_hidden(er_type)]

class ERDiagram:
    def __init__(self, colors:dict):
        self.tables = []
        self.colors = colors
    
    def add_table(self, table:Table):
        self.tables.append(table)

    def __str__(self):
        tables = '\n'.join([f'{table}' for table in self.tables])
        return f'ERDiagram {{\n{tables}\n}}'
    
    def import_from_xlsx(self, file:str):
        def get_table_type(sheet_name:str) -> tuple[str, str]:
            for table_type in self.colors['TABLE_COLOR'].keys():
                if sheet_name.lower().startswith(f"{table_type.lower()} "):
                    return table_type, sheet_name.split(f'{table_type.lower()} ')[-1]
            return None, None

        try:
            xls = pd.ExcelFile(file)
            for table_sheet in xls.sheet_names:
                table_type, table_name = get_table_type(table_sheet)
                if not table_type:
                    continue
                df = pd.read_excel(xls, table_sheet)
                column_list_pk = df.loc[df['pk'].notnull(), ['name', 'type', 'fk']].fillna('').to_dict('records')
                columns_pk = [ColumnPK(table_name, **column) for column in column_list_pk]
                column_list_fk = df.loc[df['fk'].astype(str).str.startswith("FK ") & df['pk'].isnull(), ['name', 'type', 'fk']].to_dict('records')
                columns_fk = [ColumnFK(table_name, **column) for column in column_list_fk] 
                columns_args = df.loc[df['pk'].isnull() & df['fk'].isnull(), ['name', 'type']].to_dict('records')
                columns_args = [ColumnArg(table_name, **column) for column in columns_args]

                table = Table(table_name, columns_pk, columns_fk, columns_args, type=table_type.upper())
                self.add_table(table)
        except (ColumnPK.PKErr, ColumnFK.FKErr) as e:
            return ('ERROR', e)
            pass
            
    
    def draw_pdf(self, file:str, er_type:ERType=ERType.PHYSICAL, draw_legend:bool=False, splines:str='true'):
        try:
            model_graph = graphviz.Digraph('Database', filename=file, graph_attr={'concentrate': 'true', 'rankdir': 'LR', 'splines': splines, 'overlap': 'scale'})
            for table in self.tables:
                table_struct = get_html_table(table, self.colors, er_type)
                if er_type == ERType.CONCEPTUAL:
                    model_graph.node(table.name, fillcolor=self.colors['TABLE_COLOR'][table.type]['BG_COLOR'], style='filled', shape=get_shape(er_type), fontcolor=self.colors['TABLE_COLOR'][table.type]['FONT_COLOR'])
                else:
                    model_graph.node(table.name, label=table_struct, shape=get_shape(er_type))

            for table in self.tables:
                fk_columns = table.columnsFK + [column for column in table.columnsPK if column.is_fk()]
                for fk in fk_columns:
                    model_graph.edge(f'{table.name}:{fk.name}', f'{fk.table_pk}:{fk.columnpk}',arrowhead=fk.getarrowhead(), 
                                    arrowtail=fk.getarrowtail(), dir='both', color=self.colors['ARROW_COLOR'])
            # add legend
            if draw_legend:
                for table_type in self.colors['TABLE_COLOR'].keys():
                    model_graph.node(self.colors['TABLE_COLOR'][table_type]['DESCRIPTION'], fillcolor=self.colors['TABLE_COLOR'][table_type]['BG_COLOR'], style='filled', shape='box', fontcolor=self.colors['TABLE_COLOR'][table_type]['FONT_COLOR'])
            model_graph.render(outfile=file, filename=file.replace('.pdf', '.gv'), view=True)
            return ('OK', f'{file}.pdf')
        except (ColumnPK.PKErr, ColumnFK.FKErr) as e:
            return ('ERROR', e)
            pass
        



def read_csv(file_path:str):
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        return list(reader)

def get_html_table(table:Table, colors:dict, er_type:ERType=ERType.PHYSICAL):
    if er_type == ERType.CONCEPTUAL:
        return table.name
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("html_table_template.html")
    content = template.render(table=table, er_type=er_type, colors=colors['TABLE_COLOR'], type_color=colors['TYPE_COLOR'], ERType=ERType)
    if not os.path.exists('debug'):
        os.makedirs('debug')
    with open(f"debug/{table.name}.html", mode="w", encoding="utf-8") as message:
        message.write(content)
    return content

def get_shape(er_type:ERType):
    if er_type == ERType.PHYSICAL or er_type == ERType.LOGICAL:
        return 'none'
    elif er_type == ERType.CONCEPTUAL:
        return 'box'
    else:
        print(f'ERROR: incorrect ER type {er_type}')
        raise ValueError(f'incorrect ER type {er_type}')

if __name__ == '__main__':
    #read colors from yaml file
    with open('config_colors.yml') as f:
        colors = yaml.load(f, Loader=yaml.FullLoader)
        er = ERDiagram(colors)
        er.import_from_xlsx('example/sample_datamodel.xlsx')
        er.draw_pdf('example/sample_datamodel.pdf', er_type=ERType.PHYSICAL)