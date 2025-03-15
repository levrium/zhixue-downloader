import json
import os
from pathlib import Path
import re
import threading
import time
from tkinter import filedialog
import traceback

import requests
from tqdm import tqdm

headers = [
    {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Host": "www.zhixue.com",
        "Referer": "https://www.zhixue.com/middlehomework/web-student/views/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "appName": "com.iflytek.zxzy.web.zx.stu",
        "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"'
    },
    {
        "Host": "www.zhixue.com",
        "sucOriginAppKey": "zhixue_student",
        "User-Agent": "zhixue_student/1.0.2026 (iPhone; iOS 16.2; Scale/3.00)",
        "appName": "com.zhixue.student",
        "Connection": "keep-alive",
        "Accept-Language": "zh-Hans-CN;q=1, zh-Hant-CN;q=0.9, en-CN;q=0.8",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br"
    },
    {
        "Host": "mhw.zhixue.com",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "appName": "com.zhixue.student",
        "sucOriginAppKey": "zhixue_student",
        "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        "Origin": "https://mhw.zhixue.com",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko)",
        "Referer": "https://mhw.zhixue.com/zhixuestudent/views/homeworkReport/homework-report.html",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
]

tlsysSessionId = ""
uid = ""
token = ""

lock = threading.Lock()
event = threading.Event()

def format_time(timestamp):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp // 1000))

def get(url):
    headers[1].update({"Host": url.split("/")[2], "sucUserToken": token})
    response = requests.get(url, headers=headers[1], verify=False)
    response.encoding = "utf-8"
    return response.json()

def post(url, data):
    headers[2].update({
        "Host": url.split("/")[2],
        "Origin": f'https://{url.split("/")[2]}',
        "sucUserToken": token,
        "Authorization": token
    })
    response = requests.post(url, headers=headers[2], json=data, verify=False)
    response.encoding = "utf-8"
    return response.json()

def get_token():
    global token
    response = requests.get("https://www.zhixue.com/middleweb/newToken", headers=headers[0], verify=False)
    response.encoding = "utf-8"
    response = response.json()
    result = response["result"]["token"]
    if result:
        token = result
        print(f"token: {token}")
        return True
    else:
        print("获取 token 失败。")
        return False

def parse_range(s, max_value):
    """
    将编号序列（编号从 1 开始）转换为索引列表（索引从 0 开始）。
    
    格式:
    n a-b（a 可以大于 b）
    例：1 3-5 7 10-8 -> [0, 2, 3, 4, 6, 9, 8, 7]
    """
    result = []
    for item in s.split():
        if "-" in item:
            l = item.split("-")
            if len(l) == 2 and l[0].isdigit() and l[1].isdigit():
                begin = int(l[0]) - 1
                end = int(l[1]) - 1
                if not (begin < 0 and end < 0 or begin >= max_value and end >= max_value):
                    step = -1 if begin > end else 1
                    for i in range(begin, end + step, step):
                        if 0 <= i < max_value and not i in result:
                            result.append(i)
        elif item.isdigit():
            n = int(item) - 1
            if 0 <= n < max_value and not n in result:
                result.append(n)
    return result

def to_file(file, source_type, name=""):
    """
    将各种文件信息转换为统一的格式。
    
    格式：
    name: 文件名
    path: 文件路径（若为文本则是文本内容）
    type: 文件来源（题目/答案/提交）
    is_text: 是否为文本
    """
    result = ({"name": name or Path(file).name, "path": file, "is_text": bool(name)} if isinstance(file, str) else
              {"name": name, "path": file["description"], "is_text": True} if file["fileType"] == 5 else
              {"name": file.get("name", "") or Path(file["path"]).name, "path": file["path"], "is_text": False})
    result["name"] = re.sub('[\\\\/:*?"<>|]', "_", result["name"])  # 替换文件名中的非法字符
    result["type"] = source_type
    return result

def analyze_homework(homework, include_text):
    hwId = homework["hwId"]
    hwType = homework["hwType"]
    stuHwId = homework["stuHwId"]
    file_list = []
    data = {"base": {"appId": "APP"}, "params": {"hwId": hwId, "stuHwId": stuHwId, "studentId": uid}}
    # 文件类型: 1: 图片, 2: 音频, 3: 视频, 4: 文档, 5: 文本
    
    if hwType == 102:  # 题库作业
        response = post("https://mhw.zhixue.com/hwreport/question/getStuReportDetail", data)
        if "result" in response:
            result = response["result"]
            file_list.append(to_file(result["hwDescription"], "题目", result["hwTitle"] + "_说明.txt"))
            for problem in result["mainTopics"]:
                content = problem["content"] + problem["answerHtml"] + problem["analysisHtml"]
                file_list += [to_file(path, "题目") for path in re.findall('bigger="(.+?)"', content)]
                file_list += [to_file(path, "提交") for item in problem["subTopics"] for path in item["answerResList"]]
    
    elif hwType == 105:  # 自由出题
        response = post("https://mhw.zhixue.com/hw/homework/attachment/list", data)
        file_list += [to_file(item, "题目") for item in response["result"]]
        response = post("https://mhw.zhixue.com/hwreport/question/getStuReportDetail", data)
        if "result" in response:
            result = response["result"]
            file_list.append(to_file(result["hwDescription"], "题目", result["hwTitle"] + "_说明.txt"))
            file_list += [to_file(item, "答案") for item in result.get("answerAttachList", [])]
            for problem in result["mainTopics"]:
                file_list += [to_file(path, "提交") for item in problem["subTopics"] for path in item["answerResList"]]
    
    elif hwType == 107:  # 习惯练习
        response = post("https://mhw.zhixue.com/hw/clock/answer/getClockHomeworkDetail", data)
        result = response["result"]
        file_list.append(to_file(result["description"], "题目", result["title"] + "_说明.txt"))
        file_list += ([to_file(item, "题目") for item in result.get("hwTopicAttachments", [])]
                      + [to_file(item, "答案") for item in result.get("hwAnswerAttachments", [])]
                      + [to_file(item, "答案") for item in
                         result["hwClockRecordPreviewResponses"][0].get("teacherAnswerAttachments", [])]
                      + [to_file(item, "提交", result["title"] + "_提交.txt") for item in
                         result["hwClockRecordPreviewResponses"][0].get("answerAttachments", [])])
    
    file_list = [file for file in file_list if file["path"] and (include_text or not file["is_text"])]
    return file_list

def download(file_data, path, overwrite=False):
    i = 0
    index = -2  # 路径以点号分隔后文件名（不包括后缀）的最后一部分的索引
    l = path.split(".")
    if len(l) == 1 or "\\" in l[-1]:
        index = -1
    while not overwrite and os.path.exists(path):  # 批量下载时遇到同名文件则重命名
        i += 1
        l_ = l[:]
        l_[index] += f" ({i})"
        path = ".".join(l_)
    
    if file_data["is_text"]:  # 文本直接保存
        with open(path, "w", encoding="utf-8") as file:
            file.write(file_data["path"])
        print(f"{Path(path).name} 已保存。")
    else:
        response = requests.get(file_data["path"], stream=True, verify=False)
        size = int(response.headers.get("content-length", 0))
        print(f'正在下载：{file_data["path"]}')
        print(f"文件大小：{size / 1024:.2f}KB")
        progress = tqdm(total=size, unit="B", unit_scale=True)
        with open(path, "wb") as file:
            for data in response.iter_content(chunk_size=1024):
                progress.update(len(data))
                file.write(data)
        progress.close()

def handle_queue(queue, finished):
    while not finished[0] or queue:
        event.wait()
        with lock:
            file, path = queue.pop(0)
        if not queue:
            event.clear()
        print()
        download(file, path, True)

def ask_file_names(file_list, selected_files, queue, finished):
    for i in selected_files:
        path = filedialog.asksaveasfilename(initialfile=file_list[i]["name"])
        if path:
            with lock:
                queue.append((file_list[i], path))
            event.set()
    with lock:
        finished[0] = True

def main():
    global tlsysSessionId, uid, token
    print("智学网文件下载器 2.0")
    print("对于所有需回答“是”或“否”的问题，输入任意字符代表是，直接按回车键代表否。\n")
    requests.packages.urllib3.disable_warnings()
    
    # 读取配置文件
    successful = False
    if os.path.exists("zhixue_config.json"):
        try:
            with open("zhixue_config.json", "r", encoding="utf-8") as config_file:
                config = json.loads(config_file.read())
            uid = config["uid"]
            tlsysSessionId = config["tlsysSessionId"]
            token = config["token"]
            print("读取配置文件成功。")
            headers[0].update({"Cookie": f"tlsysSessionId={tlsysSessionId}"})
            # 检验 token
            response = get(f"https://www.zhixue.com/container/app/checkToken?token={token}")
            successful = response["errorCode"] == 0
            if not successful:  # token 过期则尝试重新获取
                successful = get_token()
        except:
            print("读取配置文件失败。")
    
    while not successful:
        print("请输入 cookie：")
        while not uid:
            uid = input("ui = ")
        tlsysSessionId = input("tlsysSessionId = ")
        headers[0].update({"Cookie": f"tlsysSessionId={tlsysSessionId}"})
        successful = get_token()
    
    with open("zhixue_config.json", "w", encoding="utf-8") as config_file:
        config_file.write(json.dumps({"uid": uid, "tlsysSessionId": tlsysSessionId, "token": token}))
    print("更新配置文件成功。")
    
    # 选择学科
    response = post("https://mhw.zhixue.com/hw/answer/homework/subjects", {"base": {"appId": "APP"}, "params": {}})
    subject_codes = {}
    print()
    for item in response["result"]:
        subject_codes[item["code"]] = item["name"]
        print(f'{item["code"]}: {item["name"]}')
    print()
    subjects = input("请输入学科代码，以空格分隔（不输入默认为全部）：").split()
    subjects = [code for code in subjects if code in subject_codes]
    if len(subjects) == 0:
        subjects.append("-1")
    
    status = input("请输入要获取的作业状态（0 为未完成，1 为已完成，其他为全部）：")
    try:
        page_size = int(input("请输入单次请求的作业数量，默认为 20: "))
        if page_size <= 0:
            raise ValueError
    except ValueError:
        page_size = 20
    
    # 获取作业列表
    fetch_list = []
    if status != "1":
        fetch_list += [{"subject": subject, "status": 0} for subject in subjects]
    if status != "0":
        fetch_list += [{"subject": subject, "status": 1} for subject in subjects]
    os.system("cls")
    
    homework_list = []
    timestamps = [int(time.time() * 1000)] * len(fetch_list)  # 上次获取的最后一个作业的开始时间
    finished = [False] * len(fetch_list)
    while not all(finished):
        print("\x9B1F\x9B0J", end="")  # 清空当前行和上一行的所有内容
        index = len(homework_list)
        for i in tqdm(range(len(fetch_list)), unit=""):
            if finished[i]:
                continue
            response = get("https://mhw.zhixue.com/homework_middle_service/stuapp/getStudentHomeWorkList"
                           f'?completeStatus={fetch_list[i]["status"]}&createTime={timestamps[i]}&pageIndex=2'
                           f'&pageSize={page_size}&subjectCode={fetch_list[i]["subject"]}&token={token}')
            if response["code"] != 200:
                raise RuntimeError("获取作业列表失败")
            result_list = response["result"]["list"]
            homework_list += result_list
            if len(result_list) < page_size:
                finished[i] = True
            if result_list:
                timestamps[i] = result_list[-1]["beginTime"]
        
        # 显示作业列表
        print("\x9B1F\x9B0J", end="")
        for i in range(index, len(homework_list)):
            begin_time = format_time(homework_list[i]["beginTime"])
            end_time = format_time(homework_list[i]["endTime"])
            print(f'{i + 1}: [{subject_codes[homework_list[i]["subjectCode"]]}] '
                  f'{homework_list[i]["hwTitle"]} \t{begin_time} - {end_time}')
        print()
        if not (all(finished) or input("是否继续获取？")):
            break
    
    # 获取文件列表
    selected_homework = parse_range(input("请输入要解析的作业编号，以空格分隔，连续的范围可用两数间加-表示："), len(homework_list))
    include_text = bool(input("是否解析题目、提交的文本？"))
    print("解析作业中……")
    file_list = []
    for i in tqdm(selected_homework, unit=""):
        file_list += analyze_homework(homework_list[i], include_text)
    os.system("cls")
    print("解析作业成功。")
    
    # 选择文件
    print()
    for i in range(len(file_list)):
        print(f'{i + 1}: [{file_list[i]["type"]}] {file_list[i]["name"]}')
    print()
    selected_files = parse_range(input("请输入要下载的文件编号，以空格分隔，连续的范围可用两数间加-表示："), len(file_list))
    batch = False
    if len(selected_files) > 1:
        batch = bool(input("是否批量下载（全部下载至同一个文件夹）？"))
    
    if batch:
        rename = bool(input("是否批量重命名为连续数字？"))
        if rename:
            try:
                begin = int(input("请输入起始数字，默认为 1: "))
                if begin < 0:
                    raise ValueError
            except ValueError:
                begin = 1
            zfill = bool(input("是否在高位补 0 以统一位数？"))
            n = begin
            max_len = len(str(n + len(selected_files) - 1))
            for i in selected_files:
                new_name = str(n).zfill(max_len) if zfill else str(n)
                name = file_list[i]["name"]
                if "." in name:
                    new_name += "." + name.split(".")[-1]
                file_list[i]["name"] = new_name
                n += 1
        
        path = filedialog.askdirectory()
        if path:
            for i in selected_files:
                print()
                download(file_list[i], f'{path}/{file_list[i]["name"]}')
    
    else:
        # 使用双线程分别询问保存路径和下载文件
        queue = []
        finished = [False]
        thread_1 = threading.Thread(target=ask_file_names, args=(file_list, selected_files, queue, finished))
        thread_2 = threading.Thread(target=handle_queue, args=(queue, finished))
        thread_1.start()
        thread_2.start()
        thread_1.join()
        thread_2.join()

if __name__ == "__main__":
    while True:
        try:
            main()
        except:
            traceback.print_exc()  # 打印错误信息
        if input("\n是否重启程序？"):
            os.system("cls")
        else:
            break
