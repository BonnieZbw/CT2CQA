import requests
from openai import OpenAI


class Agent:
    def __init__(self, name) -> None:
        self.name = name
        self.OPENAI_API_KEY = "sk-4put67TH8Ft5BOQbC05cDbC1834242CeA33eDf650eDf877d"
        self.headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.OPENAI_API_KEY}"
            }
        self.url = 'https://api.chatgptapi.org.cn/v1/chat/completions'
        self.ChatHistory = []
        self.ShortMemory = []   # update top-5 turn
        self.LongMemory = []    # no change
        self.synthetic_ans = None
        self.web = None

    def Add_ChatHistory(self, chat):
        message = {"role": "assistant", "content": chat}
        self.ChatHistory.append(message)
        self.Update_ShortMemory()

    def Chat_Input(self, message):
        chat_input = []
        chat_input.extend(self.LongMemory)
        if len(self.ShortMemory) != 0 :
            chat_input.extend(self.ShortMemory)
        new_mess = {"role": "user", "content": message}
        chat_input.append(new_mess)
        self.ChatHistory.append(new_mess)
        return chat_input

    def Update_ShortMemory(self):
        if(len(self.ChatHistory) <= 10):
            try:
                self.ShortMemory = self.ChatHistory
            except Exception as e:
                print(f"Error Updata Short Memory <= 10")
        elif len(self.ChatHistory) > 10:
            try:
                self.ShortMemory = self.ChatHistory[-10:]
            except Exception as e:
                print(f"Error Updata Short Memory > 10")

    def Call_for_GPT_3(self, message):
        data = {
        # "model": "gpt-4-0125-preview",
        "model": "gpt-3.5-turbo-0125",
        "messages": message
        }
        response = requests.post(self.url, headers=self.headers, json=data).json()
        print(response)
        return response

    def Call_for_GPT_4(self, message):
        data = {
        "model": "gpt-4-0125-preview",
        # "model": "gpt-3.5-turbo-0125",
        "messages": message
        }
        response = requests.post(self.url, headers=self.headers, json=data).json()
        print(response)
        return response

    def Call_for_GPT_4vision(self, message):
        data = {
            "model": "gpt-4-vision-preview",
            "messages": message}
        response = requests.post(self.url, headers=self.headers, json=data).json()
        print(response)
        return response
    
    

    def Profile(self, profile):
        self.profile = profile
        message = [{"role": "system", "content": self.profile}]
        init_chat = self.Call_for_GPT_3(message)['choices'][0]['message']['content']
        self.LongMemory.append({"role": "system", "content": self.profile})
        self.LongMemory.append({"role": "assistant", "content": init_chat})
        # return self.profile

    
class Classification(Agent):
    def __init__(self, name) -> None:
        super().__init__(name)
        self.profile = """你是一位优秀的多模态网页问答助手。
已知问题的答案可能出现在文本、表格和统计图中,而具体到某个月份的数据大概率出现在统计图中。假设答案出现在这些模态中的概率分别为P(文本)、P(表格)和P(统计图)，且P(文本)+P(表格)+P(统计图)=1。
##模版##
Q: XXX
A: (P(文本)=a, P(统计图=b, P(表格1)=c1, ..., P(表格i)=ci)
其中，XXX是输入的问题，a和b分别是答案出现在文本和统计图中的概率，"i"指表格的数量，"P(表格i)=ci"指答案出现在第"i"个表格中的概率为"ci"，概率均为0-1的小数（精确至小数点后一位）。
你会得到##网页内容##，网页中若存在表格数据，其会以特殊的元组形式展示，你不必深入理解。你的任务是对##网页内容##进行分析，反复思考后严谨给出答案出现在每一种模态中的概率，并严格按照###模版#作答。注意，只输出##模版##要求内容。如果理解了请回复"明白"。"""
        self.Profile(self.profile)


    def Web_Template(self, web_content) -> None:
        self.web = f"""##网页内容##\n{web_content}\n如果理解了请回复"明白"。"""
        message = [{"role": "user", "content": self.web}]
        self.LongMemory.append({"role": "user", "content": self.web})
        self.LongMemory.append({"role": "assistant", "content": self.Call_for_GPT_3(message)['choices'][0]['message']['content']})

    def Remake_Question(self, message):
        if self.synthetic_ans == None:
            return message
        else:
            reamke_question = f"""上一轮问题的最终答案所在模态：{self.synthetic_ans}。\nQ: {message}"""
            return reamke_question
    
    

class Chart(Agent):
    def __init__(self, name) -> None:
        super().__init__(name)
        self.profile = """你是一位专业的统计学家，正在对一张统计图进行分析。你会得到这张统计图及其ocr结果。ocr结果中所有数值都在描述这张统计图，此外，还给出了图像中该数值对应的具体位置以及详细坐标。这些坐标以边界框(x1, y1, x2, y2)表示。这些值分别对应左上x、左上y、右下x和右下y。具体如##ocr结果##所示。
##坐标轴的基本定位方法##
1. 检查图表的横轴（x轴）和纵轴（y轴）的标签和单位。
2. 标签可能位于刻度点正下方或两个刻度之间。这种差异通常取决于数据的类型和图表的设计。具体分为两类：
    2.1 **直接对齐刻度**：当标签唯一刻度点正下方时，它直接对应该刻度的值
    2.2 **间接对齐刻度**：当标签位于两个刻度之间时，它通常表示这两个刻度的中间值或类别。
3. 定位数据点
    3.1 对于**直接对齐刻度**的标签，从标签开始，沿垂直线向上移动直至找到数据点
    3.2 对于**间接对齐刻度**的标签，首先确定标签代表的是哪两个刻度之间的值，其次从这个中间点沿垂直线向上移动直至找到数据点。
**注意：不要仅依赖颜色或图形元素来定位数据点。始终回到坐标轴的基本定位方法。**
##模版##
Q：XXX
Type：xxxxx
chart_A：xxx\nP(确信度)=a
说明：其中"XXX"是输入的问题,"Type：xxxxx"是统计图的类型，包括：单变量柱状图、分组柱状图、堆叠柱状图、单线折线图、多线折线图、饼图、折线图与柱状图的混合图或其它。"xxx"是简洁的答案，"a"是你对该答案的确信度（1-10分，分数越高，确信度越高）。
注意：如果图中没有相关答案请诚实回答："不知道"。
你会得到##ocr结果##和具体图片，发挥你作为专业统计学家的能力，先判断统计图的类别，然后按照##坐标轴的基本定位方法##解读图表，充分参考##ocr结果##提供的数值与边界框信息，严格按照###模版#作答。注意，只输出##模版##要求内容。
注意：ocr结果存在误差，你要充分结合你对统计图的解读。
如果理解了请回复"明白"。"""
        self.Profile(self.profile)
        self.client = OpenAI(api_key = "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")

    
    def Call_for_Embedding(self, message):
        embedding = self.client.embeddings.create(
        model="text-embedding-3-large",
        input=message,
        encoding_format="float"
        )
        embedding_vector = embedding.data[0].embedding
        
        return embedding_vector

    def Chat_Input(self, message, url):
        chat_input = []
        chat_input.extend(self.LongMemory)
        # if len(self.ShortMemory) != 0 :
        #     chat_input.extend(self.ShortMemory)
        new_mess = {"role": "user","content": [
                {
                    "type": "text",
                    "text": message
                },
                {
                    "type": "image_url",
                    "image_url": url
                }]
        }
        chat_input.append(new_mess)
        self.ChatHistory.append(new_mess)
        return chat_input

    def Remake_Question(self, question, ocr):
        new_prompt = f"""##ocr结果##\n{ocr}\nQ:{question}"""
        return new_prompt



class Table(Agent):
    def __init__(self, name) -> None:
        super().__init__(name)
        self.profile = """你是一位专业的数据分析师，正在以一种新的规则阅读表格，具体规则如##规则##所示：
##规则##
本规则将表格的所有单元格分为如下三类：  1、('T', 起始, 终止, 值)表示列标题单元格；  2、('L', 起始, 终止, 值)表示行标题单元格； 3、('C', 行, 列, 值)表示数值单元格。  除'T'、'L'、'C'外，其余元素均为具体数值。其中，'T'指该元组表示一个列标题单元格；'L'指该元组表示一个行标题单元格；'C'指该元组表示一个数值单元格；'起始'与'终止'分别指该行（或列）标题从第几行（或列）开始，到第几行（或列）结束；'行'与'列'分别指该数值单元格所处的行和列；'值'指该单元格中存储的数值。注意，当列标题单元格的'起始'与'终止'数值不等时，所有['起始', '终止']间的列标题单元格都为其子标题单元格；行标题同理。例："元组1：('T', 0, 1, 3, 2000年)，元组2：('T', 1, 1, 1, 1-6月)，元组1的'起始'与'终止'数值不等，所有[1, 3]间的列标题单元格都为其子标题，元组2的['起始', '终止']为[1, 1]，因此元组2为元组1的子标题，若需要查询'2000年1-6月的某数值，则应该先找到描述2000年的元组1，并根据其['起始', '终止']范围，找到描述"1-6"月的子标题元组2"。
##模版##
Q：XXX
table_A：xxx\nP(确信度)=a
说明：其中"XXX"是输入的问题,"xxx"是简洁的答案，"a"是你对该答案的确信度（1-10分，分数越高，确信度越高）。
注意：如果表中没有相关答案请诚实回答："不知道"。
你会得到##表格信息##，发挥你作为专业数据分析师的能力，基于##规则##，对##表格信息##中的内容进行深入理解，并严格按照##模版##作答。注意，只输出##模版##要求内容。如果理解了请回复"明白"。
"""
        self.Profile(self.profile)
        self.table_list = []

    def Remake_Question(self, question, table_num):
        for item in self.table_list:
            if item['num'] == table_num:
                table_content = item['content']
        new_prompt = f"##表格信息##\n{table_content}\nQ: {question}"
        return new_prompt
    
    def Add_Table(self, table_num, table_content):
        exists = any(item['num'] == table_num for item in self.table_list)
        if exists:
            print(f"已存在Table{table_num}")
        else:
            new_content = {"num": table_num, "content": table_content}
            self.table_list.append(new_content)
            print(f"成功添加Table{table_num}")
            
    def Chat_Input(self, message):
        chat_input = []
        chat_input.extend(self.LongMemory)
        new_mess = {"role": "user", "content": message}
        chat_input.append(new_mess)
        self.ChatHistory.append(new_mess)
        return chat_input


class Text(Agent):
    def __init__(self, name) -> None:
        super().__init__(name)
        self.profile = """你是一位优秀的的经济分析师，正在阅读网页内容。
##模版##
Q：XXX
text_A：xxx\nP(确信度)=a
说明：其中"XXX"是输入的问题,"xxx"是简洁的答案，"a"是你对该答案的确信度（1-10分，分数越高，确信度越高）。
注意：如果文中没有相关答案请诚实回答："不知道"。
你会得到##网页信息##，发挥你作为专业经济分析师的能力，对##网页信息##深入分析后严格基于##模版##作答。注意，只输出##模版##要求内容。如果理解了请回复"明白"。"""
        self.Profile(self.profile)
    
    def Web_Template(self, web_content) -> None:
        self.web = f"""##网页信息##\n{web_content}\n如果理解了请回复"明白"。"""
        message = [{"role": "user", "content": self.web}]
        self.LongMemory.append({"role": "user", "content": self.web})
        self.LongMemory.append({"role": "assistant", "content": self.Call_for_GPT_3(message)['choices'][0]['message']['content']})


    def Remake_Question(self, question):
        new_question = f"Q: {question}"
        return new_question
    
class Synthetic_Agent(Agent):
    def __init__(self, name) -> None:
        super().__init__(name)
        self.profile = """你是一位专业的数据综合分析师，正在对同一个答案的不同回答作出综合判断。已知具体到某个月份的数据大概率出现在统计图中。
##答案说明##
Q: xxx
text_A: XXX
P(确信度)=a
chart_A: XXX
P(确信度)=b
table_A: XXX
P(确信度)=c
...
其中，"Q: xxx"指问题，"text_A: XXX"，"chart_A: XXX"和"table_A: XXX"分别指文本、统计图和表格模态分析后的答案，"P(确信度)"表示对该答案的确信度（1-10分，分数越高，确信度越高）。

##模版##
A: XXX
模态: xxx
其中，"XXX"是你选取的最可信的答案，"xxx"是答案所在的模态（只能是text、chart或table）。

你会得到##答案列表##，发挥你作为数据综合分析师的能力，基于##答案说明##，对##答案列表##进行分析后，严格基于##模版##作答。注意，只输出##模版##要求内容。如果理解了请回复"明白"。
"""
        self.Profile(self.profile)


    def Remake_Question(self, question, text_ans, table_ans, chart_ans):
        new_question = f"##答案列表##\nQ: {question}\n"
        if text_ans is not None:
            new_question += text_ans + '\n'
        if chart_ans is not None:
            new_question += chart_ans + '\n'
        if table_ans is not None:
            for ans in table_ans:
                new_question += str(ans) + '\n'
        return new_question
    