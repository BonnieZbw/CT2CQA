import html2tuple

def table_json2tuple(item):
    if item["type"] == "C":
        return ("C", item["row_index"], item["column_index"], item["value"])
    elif item["type"] == "L":
        return ("L", item["row_index"], item["end_index"], item["value"])
    elif item["type"] == "T":
        return ("T", item["start_column"], item["end_column"], item["value"])
    

def table2tuple(table_path):
    items = html2tuple.solve(table_path)
    tuples = []
    for item in items:
        tuples.append(table_json2tuple(item))
    return tuples
    
