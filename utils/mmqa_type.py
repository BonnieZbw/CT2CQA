import numpy as np
import bs4
import re
from abc import ABC

class ColumnHeader(ABC):
    def __init__(self, ex_hierarchical_index, start_column, end_column, value):
        self.type = 'T'
        self.ex_hierarchical_index = ex_hierarchical_index
        self.start_column = start_column
        self.end_column = end_column
        self.value = value

    def __str__(self):
        return f"ColumnHeader(T={self.type}, ex_hierarchical_index={self.ex_hierarchical_index}, start_column={self.start_column}, end_column={self.end_column}, value={self.value})"
    
    def to_dict(self):
        return {
            'type': self.type,
            'ex_hierarchical_index': self.ex_hierarchical_index,
            'start_column': self.start_column,
            'end_column': self.end_column,
            'value': self.value
        }

class RowHeader(ABC):
    def __init__(self,im0hierarchical_index, row_index, value, end_index=None):
        self.type = 'L'
        self.im0hierarchical_index = im0hierarchical_index
        self.row_index = row_index
        self.value = value
        
        #针对复杂的行标题
        self.end_index = end_index if end_index else row_index

    def __str__(self):
        return f"RowHeader(L={self.type}, im0hierarchical_index={self.im0hierarchical_index}, row_index={self.row_index}, end_index={self.end_index}, value={self.value})"
    
    def to_dict(self):
        return {
            'type': self.type,
            'im0hierarchical_index': self.im0hierarchical_index,
            'row_index': self.row_index,
            'end_index': self.end_index,
            'value': self.value
        }

class Cell(ABC):
    def __init__(self, row_index, column_index, value):
        self.type = 'C'
        self.row_index = row_index
        self.column_index = column_index - 1
        self.value = value

    def __str__(self):
        return f"Cell(C={self.type}, row_index={self.row_index}, column_index={self.column_index}, value={self.value})"
    
    def to_dict(self):
        return {
            'type': self.type,
            'row_index': self.row_index,
            'column_index': self.column_index,
            'value': self.value
        }

class Marker:
    def __init__(self, row_num, col_num):
        self.row_num = row_num
        self.col_num = col_num
        self.m = np.ones((row_num, col_num))
    
    def reset(self):
        self.m = np.ones((self.row_num, self.col_num))

    def get_next(self, row_num):
        if 0 <= row_num < self.row_num:
            for col_num in range(self.col_num):
                # print(f"[DEBUG] row_num: {row_num}, col_num: {col_num} mshape: {self.m.shape}")
                if self.m[row_num, col_num] == 1:
                    return col_num  
        return None 

    def mark(self, row, column, row_span, col_span):
        end_row = min(row + row_span, self.row_num)
        end_col = min(column + col_span, self.col_num)

        for i in range(row, end_row):
            for j in range(column, end_col):
                self.m[i, j] = 0

class HtmlRanker:
    def __init__(self) -> None:
        self.queue = []
        self.str_pattern = [
            r'[一二三四五六七八九十百千万亿]+、',
            r'[\(\（][一二三四五六七八九十百千万亿0-9]+[\)\）].*'
        ]
        self.space_rank_pattern = r'^\s*(一|二|三|四|五|六|七|八|九|十)、|其中：'
    
    # 加粗样式idx设计为100，正常样式为0
    def hit_rank(self, td:bs4.element.Tag):
        value = td.get_text().strip().strip('\n')
        for idx,pattern in enumerate(self.str_pattern):
            match = re.search(pattern, value)
            if match:
                return idx
        if td.find('b') or ('font-weight' in td.attrs.get('style', '') and 'bold' in td['style']):
            return 100
        return -1


    def reset(self):
        self.queue = []


    def pad_with_spaces(self, s, desired_length):
        # 使用字符串的格式化方法来添加空格
        return f"{s:>{desired_length}}"
    

    def search_queue(self, style):
        for idx,que in enumerate(self.queue):
            if que == style:
                return idx
        return -1
    

    def space_rank(self, td:bs4.element.Tag):
        value = td.get_text().strip('\n')
        value_re = re.sub(self.space_rank_pattern,' ',value)
        value_re = self.pad_with_spaces(value_re, len(value))
        # print(f"[INFO] value final is now {value_re}")
        space_count = len(value_re) - len(value_re.strip())
        return space_count

    def get_rank(self, td:bs4.element.Tag):
        # rank = self.hit_rank(td)
        rank = self.space_rank(td)
        value = td.get_text().strip('\n')
        print(f"[DEBUG] value is now {value}, space_count is now: {rank}, queue is now {self.queue}")

        #首个元素
        if len(self.queue) == 0:
            # print(f"[DEBUG] first set rank: {rank}, value:{td.get_text().strip()}")
            self.queue.append(rank)
            return 0
        
        search_pos = self.search_queue(rank)
        print(f"[DEBUG] search_pos: {search_pos}")
        if search_pos == -1:
            self.queue.append(rank)
        else:
            self.queue = self.queue[:search_pos+1]

        
        return len(self.queue) - 1
        #和上个元素相同
        if rank == self.queue[-1]:
            # print("[DEBUG] rank==-1")
            return len(self.queue) - 1
        
        #和上个元素不同 但和-2元素相同
        elif len(self.queue) > 1 and rank == self.queue[-2]:
            # print("[DEBUG] rank==-2")
            self.queue.pop(-1)
            return len(self.queue) - 1
        
        #都不相同，需要加深
        else:
            # print("[DEBUG] rank==3")
            self.queue.append(rank)
            return len(self.queue) - 1


class RowRanker():
    def __init__(self) -> None:
        self.clock = []

    def step(self):
        self.clock = [clock - 1 for clock in self.clock]
        self.clock = [clock for clock in self.clock if clock != 0]

    def get_rank(self):
        return len(self.clock) + 1
        
    def add_clock(self, num):
        self.clock.append(num)