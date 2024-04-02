from langchain_openai import OpenAI
from langchain.memory import ChatMessageHistory
from langchain_community.chat_models import ChatOpenAI
from paddleocr import PaddleOCR
import os
import json
import Agent_base
import re
import numpy as np
from numpy import dot
import math
import csv

# Classi_Agent
def get_probablity(ans):
    parts = ans.split(',')
    text_p = None
    chart_p = None
    table_p = []
    table_num = []
    for part in parts:
        if "文本" in part:
            text_p = float(part.split("=")[-1].split(")")[0])
        if "统计图" in part:
            chart_p = float(part.split("=")[-1].split(")")[0])
        if "表格" in part:
            table_num.append(re.findall(r'\d+', part)[0])
            table_p.append(float(part.split("=")[-1].split(")")[0]))
    return text_p, table_p, chart_p, table_num


def classification(Classification_Agent, question):
    # print(f"Class Long Memo: {Classification_Agent.LongMemory}")
    # print(f"Class Short Memo: {Classification_Agent.ShortMemory}")
    # print(f"Class Chat His: {Classification_Agent.ChatHistory}")
    # print(f"Synthetic ans: {Classification_Agent.synthetic_ans}")
    question = Classification_Agent.Remake_Question(question)
    # print(f"New question: {question}")
    prompt = Classification_Agent.Chat_Input(question)
    # print(f"New input: {prompt}")
    ans = Classification_Agent.Call_for_GPT_4(prompt)['choices'][0]['message']['content']
    # print(f"Class Ans: {ans}")
    Classification_Agent.Add_ChatHistory(ans)
    # print(f"Class Long Memo: {Classification_Agent.LongMemory}")
    # print(f"Class Short Memo: {Classification_Agent.ShortMemory}")
    # print(f"Class Chat His: {Classification_Agent.ChatHistory}")
    return get_probablity(ans)


def if_activate(p):
    if p is not None and p > 0.1:
        return 1
    else:
        return 0
    

def table_json2tuple(item):
    if item["type"] == "C":
        return ("C", item["row_index"], item["column_index"], item["value"])
    elif item["type"] == "L":
        return ("L", item["row_index"], item["end_index"], item["value"])
    elif item["type"] == "T":
        return ("T", item["start_column"], item["end_column"], item["value"])

# Table_Agent
def table_(table_num, Table_Agent, question, index):
    # print("Table Agent Activate")
    # print(f"Table numb: {table_num}")
    # print(f"Table Long Memo: {Table_Agent.LongMemory}")
    # print(f"Table Short Memo: {Table_Agent.ShortMemory}")
    # print(f"Table Chat His: {Table_Agent.ChatHistory}")
    table_path = f"../data_base/{index}/content/table{table_num}.json"
    table_content = []
    with open(table_path, 'r', encoding="utf-8")as f:
        table_data = json.load(f)
    for item in table_data:
        table_content.append(table_json2tuple(item))
    Table_Agent.Add_Table(table_num, table_content)
    new_question = Table_Agent.Remake_Question(question, table_num)
    prompt = Table_Agent.Chat_Input(new_question)
    # print(f"Table input {prompt}")
    ans = Table_Agent.Call_for_GPT_3(prompt)['choices'][0]['message']['content']
    # print(f"Table Ans: {ans}")
    Table_Agent.Add_ChatHistory(ans)
    # print(f"Table Long Memo: {Table_Agent.LongMemory}")
    # print(f"Table Short Memo: {Table_Agent.ShortMemory}")
    # print(f"Table Chat His: {Table_Agent.ChatHistory}")
    return ans



# Text_Agent
def text_(text, Text_Agent, question):
    # print("Text Agent Activate")
    # print(f"Text Long Memo: {Text_Agent.LongMemory}")
    # print(f"Text Short Memo: {Text_Agent.ShortMemory}")
    # print(f"Text Chat His: {Text_Agent.ChatHistory}")
    Text_Agent.Web_Template(text)
    new_question = Text_Agent.Remake_Question(question)
    prompt = Text_Agent.Chat_Input(new_question)
    # print(f"Text input: {prompt}")
    ans = Text_Agent.Call_for_GPT_3(prompt)['choices'][0]['message']['content']
    # print(f"Text Ans: {ans}")
    Text_Agent.Add_ChatHistory(ans)
    # print(f"Text Long Memo: {Text_Agent.LongMemory}")
    # print(f"Text Short Memo: {Text_Agent.ShortMemory}")
    # print(f"Text Chat His: {Text_Agent.ChatHistory}")
    return ans



# 修改输入格式为仿Llava
def paddle_ocr(url):
    result_llava = {}
    ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False, det_db_score_mode="slow")  # need to run only once to download and load model into memory
    result = ocr.ocr(url, cls=True)
    # print(result)
    boxes = np.array([line[0] for line in result[0]], dtype=float)
    txts = np.array([line[1][0] for line in result[0]])
    # print(boxes, txts)
    for i in range(len(boxes)):
        bbox = boxes[i]
        value = txts[i]
        coords = [bbox[0][0], bbox[0][1], bbox[2][0], bbox[2][1]]
        if value in result_llava:
            result_llava[value].append(coords)
        else:
            result_llava[value] = [coords]    
    # print(result_llava)
    return result_llava, txts



def count_similarity(Chart_Agent, question, ocr_result):
    question_embedding = Chart_Agent.Call_for_Embedding(question)
    concat_ocr = ""
    for res in ocr_result:
        if re.search("[\u4e00-\u9fff]", res):
            concat_ocr += res
    ocr_embedding = Chart_Agent.Call_for_Embedding(concat_ocr)
    similarity = dot(question_embedding, ocr_embedding)
    # print(f"similarity: {similarity}")
    return similarity


def select_candidates(Chart_Agent, question, urls):
    similarity_list = []
    url_message = []
    img_path = []
    # print(urls)
    for url in urls:
        url = url[0]
        img_path.append("../data_base"+url.split('MMQA')[-1])
    # print(f"img_path {img_path}")
    for url in img_path:
        ocr_result, txt = paddle_ocr(url)
        url_message.append(ocr_result)
        similarity_list.append(count_similarity(Chart_Agent, question, txt))
    full_list = zip(urls, similarity_list, url_message)
    # print(full_list)
    candidate = sorted(full_list, key=lambda x: x[1], reverse=True)[0]
    # print(candidate)
    return candidate


# Chart Agent
def chart_(Chart_Agent, question, urls):
    # print("Chart Agent Activate")
    # print(f"Chart Long Memo: {Chart_Agent.LongMemory}")
    # print(f"Chart Short Memo: {Chart_Agent.ShortMemory}")
    # print(f"Chart Chat His: {Chart_Agent.ChatHistory}")
    candidate = select_candidates(Chart_Agent, question, urls)
    # print(candidate)
    # candidate[0]-img bed, candidate[1]-similarity, candidata[2]-ocr result
    new_question = Chart_Agent.Remake_Question(question, candidate[2])
    prompt = Chart_Agent.Chat_Input(new_question, candidate[0][0])
    # print(f"Prompt: {prompt}")
    ans = Chart_Agent.Call_for_GPT_4vision(prompt)['choices'][0]['message']['content']
    # print(f"Ans: {ans}")
    Chart_Agent.Add_ChatHistory(ans)
    # print(f"Chart Long Memo: {Chart_Agent.LongMemory}")
    # print(f"Chart Short Memo: {Chart_Agent.ShortMemory}")
    # print(f"Chart Chat His: {Chart_Agent.ChatHistory}")
    return ans



def Synthetic_postprocess(synthetic):
    ans = synthetic.split('\n')[0].split(':')[-1].strip()
    modal = synthetic.split('\n')[-1].split(':')[-1].strip()
    return ans, modal

# Synthetic_Agent
def Synthetic(Synthetic_Agent, text_ans, table_ans, chart_ans, question):
    # print("Synthetic Agent Activate")
    # print(f"Synthetic Long Memo: {Synthetic_Agent.LongMemory}")
    # print(f"Synthetic Short Memo: {Synthetic_Agent.ShortMemory}")
    # print(f"Synthetic Chat His: {Synthetic_Agent.ChatHistory}")
    new_question = Synthetic_Agent.Remake_Question(question, text_ans, table_ans, chart_ans)
    prompt = Synthetic_Agent.Chat_Input(new_question)
    # print(f"Synthetic input: {prompt}")
    ans = Synthetic_Agent.Call_for_GPT_4(prompt)['choices'][0]['message']['content']
    # print(f"Synthetic ans: {ans}")
    Synthetic_Agent.Add_ChatHistory(ans)
    final_ans, modal = Synthetic_postprocess(ans)
    return final_ans, modal

def main(web_content, questions, urls, text, index, ans):
    Classification_Agent = Agent_base.Classification("Classification")
    Classification_Agent.Web_Template(web_content)
    Text_Agent = Agent_base.Text("Text")
    Table_Agent = Agent_base.Table("Table")
    Chart_Agent = Agent_base.Chart("Chart")
    Synthetic_Agent = Agent_base.Synthetic_Agent("Synthetic")
    for i in range(len(questions)):
        try:
            question = questions[i]
            gold_ans = ans[i]
            text_p, table_p, chart_p, table_num = classification(Classification_Agent, question)
            print(f"Ptext={text_p}, Pchart={chart_p}, Ptable={table_p}")
            table_ans = []
            text_ans = None
            chart_ans = None
            if if_activate(text_p):
                text_ans = text_(text, Text_Agent, question)
            if if_activate(chart_p):
                chart_ans = chart_(Chart_Agent, question, urls)
            for i in range(len(table_p)):
                if if_activate(table_p[i]):
                    table_ans.append(table_(table_num[i], Table_Agent, question, index))
            final_ans, new_Synthetic = Synthetic(Synthetic_Agent, text_ans, table_ans, chart_ans, question)
            Classification_Agent.synthetic_ans = new_Synthetic
            # print(f"Class Long Memo: {Classification_Agent.LongMemory}")
            # print(f"Class Short Memo: {Classification_Agent.ShortMemory}")
            # print(f"Class Chat His: {Classification_Agent.ChatHistory}")
            print(f"Final answer: {final_ans}")
            with open("./ans.csv", 'a', newline='', encoding="utf-8")as f:
                writer = csv.writer(f)
                writer.writerow([gold_ans, final_ans])
            # print(f"Synthetic_ans{Classification_Agent.synthetic_ans}")
        except Exception as e:
            print(f"Error: {e}")
            with open("./ans.csv", 'a', newline='', encoding="utf-8")as f:
                writer = csv.writer(f)
                writer.writerow([gold_ans, f"**Error**{e}"])

    return ans
            



def load_data():
    for i in range(0, 1):
        try:
            questions = []
            ans = []
            urls = []
            qa_path = f"../data_base/{i}/qa"
            for item in os.listdir(qa_path):
                full_path = os.path.join(qa_path, item)
                with open(full_path, 'r')as f: 
                    data = json.load(f)
                for item in data:
                    questions.append(item['question'])
                    ans.append(item['answer'])
            with open(f"../data_base/{i}/content/url_list.csv", 'r', encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    urls.append(row)
            with open(f"../data_base/{i}/content/web_content{i}.md", 'r', encoding="utf-8") as f:
                web_content = f.read()
            with open(f"../data_base/{i}/content/{i}.md", 'r', encoding="utf-8") as f:
                text = f.read()
            print(len(questions),flush=True)
            gen_ans = main(web_content, questions, urls, text, i, ans)
            print(gen_ans)
            # print(len(questions), len(ans))
            
        except Exception as e:
            print(f"Error: {e}")
            
            
        # main(web_content, question, urls)

load_data()