from bs4 import BeautifulSoup
import bs4
from typing import List
from pprint import pprint
from utils.mmqa_type import ColumnHeader, RowHeader, Cell, Marker, HtmlRanker, RowRanker
import fire
import json

def parse_html(doc_path:str) -> BeautifulSoup():
    with open(doc_path,'r',encoding='utf-8') as file:
        html_content = file.read()
    soup = BeautifulSoup(html_content,'html.parser')
    return soup


def soup_parse(source, pattern:str) -> List:
    return source.find_all(pattern)


def get_table_shape(table):
    column_num = sum([int(item.get('colspan',1)) for item in table.find_all('tr')[-2].find_all('td')])
    row_num = int(table.find_all('tr')[0].find_all('td')[0].get('rowspan',1))

    return row_num, column_num


def parse_header_from_thead(table) -> List:
    thead = soup_parse(table,'thead')
    if len(thead) == 0:
        return None
    
    cols:List[ColumnHeader] = []
    trs:List[bs4.element.Tag] = soup_parse(thead[0],'tr')

    row, column = get_table_shape(table)
    
    #有thead的时候，thead里的行数就是列标题层级数
    row = len(trs)

    # print(f"[DEBUG] row:{row}, column:{column}")
    marker = Marker(row,column)

    #每个<tr>为table的一行
    for row_id,tr in enumerate(trs):
        tds: List[bs4.element.Tag] = soup_parse(tr, 'td')
        
        #每个<td>为table的一列
        for col_id, td in enumerate(tds):
            row_span = int(td.get('rowspan')) if td.get('rowspan') else 1
            col_span = int(td.get('colspan')) if td.get('colspan') else 1
            value = td.get_text().strip().strip('\n')

            start_col = marker.get_next(row_id)
            # print(f"[DEBUG] start_col: {start_col}, col_span: {col_span} row_id: {row_id} row_span: {row_span}")
            end_col = start_col + col_span - 1
            marker.mark(row_id,start_col,row_span,col_span)

            if len(value) == 0 and td.get('nowrap') == "nowrap":
                cols[-1].end_column = end_col
            else:
                cols.append(ColumnHeader(
                    ex_hierarchical_index=row_id,
                    start_column=start_col,
                    end_column=end_col,
                    value=value,
                ))

    # 如果前一半和后一半完全相同 只保留一半就好
    if len(cols) % 2 == 0 and cols[:len(cols)//2] == cols[len(cols)//2:]:
        return cols[:len(cols)//2]
    return cols


# 当thead不存在时，用前row行拼接成header
def parse_header_from_tbody(table):
    row, column = get_table_shape(table)
    # print(f"[DEBUG] row: {row}, column: {column}")
    header_rows:List[bs4.element.Tag] = soup_parse(table,'tr')[:row]

    marker = Marker(row,column+1)
    cols:List[ColumnHeader] = []

    for row_id, tr in enumerate(header_rows):
        tds: List[bs4.element.Tag] = soup_parse(tr,'td')

        for col_id, td in enumerate(tds):
            row_span = int(td.get('rowspan')) if td.get('rowspan') else 1
            col_span = int(td.get('colspan')) if td.get('colspan') else 1
            value = td.get_text().strip().strip('\n')

            start_col = marker.get_next(row_id)
            # print(f"[DEBUG] start_col: {start_col}, col_span: {col_span} row_id: {row_id} row_span: {row_span}")
            end_col = start_col + col_span - 1
            marker.mark(row_id,start_col,row_span,col_span)

            if len(value) == 0 and td.get('nowrap') == "nowrap":
                cols[-1].end_column = end_col
            else:
                cols.append(ColumnHeader(
                    ex_hierarchical_index=row_id,
                    start_column=start_col,
                    end_column=end_col,
                    value=value,
                ))
    return cols


def parse_row_cell_from_table(table):
    row, column = get_table_shape(table)

    tbody = table.find_all('tbody')
    assert len(tbody) == 1 , "Tbody should hape len==1"

    # print(tbody)
    trs = tbody[0].find_all('tr')

    # 如果标题直接在tbody中，跳过head部分，并且index从1开始
    if not parse_header_from_thead(table):
        trs = trs[row:]
    
    cells:List[Cell] = []
    row_headers:List[RowHeader] = []
    ranker = HtmlRanker()
    
    # 每一行，包含 Row + Cell
    for row_id, tr in enumerate(trs):
        # print(f"[INFO] idx: {row_id}, tr: {tr}")

        tds:List[bs4.element.Tag] = tr.find_all('td')
        for col_id, td in enumerate(tds):
            value = td.get_text().strip().strip('\n')
            #行
            if col_id == 0:
                rank = ranker.get_rank(td)
                # print(f"[DEBUG] rol read: {value}")
                headers = RowHeader(
                    im0hierarchical_index=rank,
                    row_index=row_id + 1,
                    value=value
                )
                row_headers.append(headers)
            else:
                cell = Cell(
                    row_index=row_id + 1,
                    column_index=col_id + 1,
                    value=value
                )
                cells.append(cell)
                # print(cells[-1])
    
    return row_headers, cells


def check_all_thead(soup):
    thead = soup_parse(soup, "thead")
    tbody = soup_parse(soup, "tbody")

    print(f"[INFO] thead: {len(thead)}, tbody: {len(tbody)}")

    if len(tbody) == 0:
        return True
    if len(thead) == 0:
        return False
    thead_trs = soup_parse(thead[0], 'tr')
    tbody_trs = soup_parse(tbody[0], 'tr')

    if len(thead_trs) != 0 and len(tbody_trs) == 0:
        return True
    return False


def all_thead_parse_header_from_thead(table) -> List:
    shape = get_table_shape(table)
    thead = soup_parse(table,'thead')

    cols:List[ColumnHeader] = []
    trs:List[bs4.element.Tag] = soup_parse(thead[0],'tr')

    row, column = get_table_shape(table)

    marker = Marker(row,column)

    #每个<tr>为table的一行
    for row_id,tr in enumerate(trs[:row]):
        tds: List[bs4.element.Tag] = soup_parse(tr, 'td')
        
        #每个<td>为table的一列
        for col_id, td in enumerate(tds):
            row_span = int(td.get('rowspan')) if td.get('rowspan') else 1
            col_span = int(td.get('colspan')) if td.get('colspan') else 1
            value = td.get_text().strip().strip('\n')

            start_col = marker.get_next(row_id)
            # print(f"[DEBUG] start_col: {start_col}, col_span: {col_span} row_id: {row_id} row_span: {row_span}")
            end_col = start_col + col_span - 1
            marker.mark(row_id,start_col,row_span,col_span)

            if len(value) == 0 and td.get('nowrap') == "nowrap":
                cols[-1].end_column = end_col
            else:
                cols.append(ColumnHeader(
                    ex_hierarchical_index=row_id,
                    start_column=start_col,
                    end_column=end_col,
                    value=value,
                ))
    
    return cols


def all_thead_parse_row_cell_from_table(soup):
    row, column = get_table_shape(soup)
    thead = soup_parse(soup, 'thead')

    cols:List[ColumnHeader] = []
    trs:List[bs4.element.Tag] = soup_parse(thead[0],'tr')

    trs = trs[row:]

    cells:List[Cell] = []
    row_headers:List[RowHeader] = []
    ranker = HtmlRanker()

    # 每一行，包含 Row + Cell
    for row_id, tr in enumerate(trs):
        # print(f"[INFO] idx: {row_id}, tr: {tr}")

        tds:List[bs4.element.Tag] = tr.find_all('td')
        for col_id, td in enumerate(tds):
            value = td.get_text().strip().strip('\n')
            #行
            if col_id == 0:
                #TODO: Support Multi Rows
                rank = ranker.get_rank(td)
                # print(f"[DEBUG] rol read: {value}")
                headers = RowHeader(
                    im0hierarchical_index=rank,
                    row_index=row_id + 1,
                    value=value
                )
                row_headers.append(headers)
            else:
                cell = Cell(
                    row_index=row_id + 1,
                    column_index=col_id,
                    value=value
                )
                cells.append(cell)
                # print(cells[-1])
    
    return row_headers, cells


def row_span_in_tbody_exist(table):
    row, column = get_table_shape(table)

    tbody = table.find_all('tbody')
    assert len(tbody) == 1 , "Tbody should hape len==1"

    trs = tbody[0].find_all('tr')

    # 如果标题直接在tbody中，跳过head部分，并且index从1开始
    if not parse_header_from_thead(table):
        trs = trs[row:]

    for row_id, tr in enumerate(trs):
        tds = tr.find_all('td')
        for col_id, td in enumerate(tds):
            row_span = int(td.get('rowspan')) if td.get('rowspan') else 1
            if row_span != 1:
                return True
    
    return False


def  parse_row_cell_from_table_complex_row(table):
    row, column = get_table_shape(table)

    tbody = table.find_all('tbody')
    assert len(tbody) == 1 , "Tbody should hape len==1"

    # print(tbody)
    trs = tbody[0].find_all('tr')

    # 如果标题直接在tbody中，跳过head部分，并且index从1开始
    if not parse_header_from_thead(table):
        trs = trs[row:]
    
    cells:List[Cell] = []
    row_headers:List[RowHeader] = []

    ranker = RowRanker()

    for row_id, tr in enumerate(trs):
        tds:List[bs4.element.Tag] = tr.find_all('td')
        after_L = False

        ranker.step()
        row_type = ""

        for col_id, td in enumerate(tds):
            value = td.get_text().strip('\n').strip()
            row_span = int(td.get('rowspan')) if td.get('rowspan') else 1
            rank = ranker.get_rank()

            #多行的L
            if row_span != 1:
                headers = RowHeader(
                    im0hierarchical_index=rank,
                    row_index = row_id + 1,
                    value=value,
                    end_index = row_id + row_span,
                )
                row_headers.append(headers)
                after_L = True
                ranker.add_clock(row_span)
                row_type = 'row_span'
            
            #仍然是L，但前边是多行L
            elif after_L:
                headers = RowHeader(
                    im0hierarchical_index = rank,
                    row_index = row_id + 1,
                    value = value,
                )
                row_headers.append(headers)
                after_L = False

            elif col_id == 0:
                headers = RowHeader(
                    im0hierarchical_index = rank,
                    row_index = row_id + 1,
                    value = value
                )
                row_headers.append(headers)
                row_type = 'normal'
            else:
                rank = ranker.get_rank()
                print(f"[DEBUG] rank now: {rank}, value now: {value} ranker now : {ranker.clock}")

                if row_type == 'row_span':
                    col_index = col_id + 1
                elif row_type == 'normal':
                    col_index = col_id + ranker.get_rank()
                else:
                    col_index = -1

                cell = Cell(
                    row_index = row_id + 1,
                    column_index = col_index,
                    value = value
                )
                cells.append(cell)
    
    return row_headers, cells


def solve(
        html_path: str,
        save_path: str = None
        ):
    soup = parse_html(html_path)

    #特判1: 如果所有数据都在thead，则全部解析thead处理
    if check_all_thead(soup):
        columns = all_thead_parse_header_from_thead(soup)
        headers, cells = all_thead_parse_row_cell_from_table(soup)

        results = columns + headers + cells
        results = [res.to_dict() for res in results]

        if save_path:
            with open(save_path,'w',encoding='utf-8') as file:
                json.dump(results, file, indent=4,ensure_ascii=False)

    #常规处理
    else:   
        #确定表格列标题
        thead = parse_header_from_thead(soup)
        columns = thead if thead else parse_header_from_tbody(soup)

        print(f"[DEBUG] thead: {thead}")

        for col in columns:
            print(f"[DEBUG] col: {col}")

        if row_span_in_tbody_exist(soup):
            headers, cells = parse_row_cell_from_table_complex_row(soup)
        else:
            headers, cells = parse_row_cell_from_table(soup)
        
        for head in headers:
            print(f"[DEBUG] header: {head}")

        for cell in cells:
            print(f"[DEBUG] cell: {cell}")

        results = []
        results.extend(columns)
        results.extend(headers)
        results.extend(cells)

        results = [res.to_dict() for res in results]

        if save_path:
            with open(save_path,'w',encoding='utf-8') as file:
                json.dump(results, file, indent=4,ensure_ascii=False)
        return results



def debug(html_path:str):
    soup = parse_html(html_path)
    table = soup.find_all('table')[0]
    h = table.find_all('tr')[0]
    print(h)
    


def main(html_path: str):
    soup = parse_html(html_path)

    table = soup.find_all('table')
    assert len(table) == 1

    table = table[0]

    rows = soup_parse(table, 'tr')

    tds = soup_parse(rows[0], 'td')
    for item in tds:
        print(f"[INFO] td: {item}")

    


if __name__ == "__main__":
    fire.Fire(solve)