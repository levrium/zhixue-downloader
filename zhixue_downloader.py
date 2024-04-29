import json
import os
from pathlib import Path
import re
import time

import requests
from tqdm import tqdm
import win32con
import win32ui

headers = [{}, {}]
userId = ""
token = ""

def read_HAR_file(path):
    global headers, userId, token
    urls = [
        ["https://mhw.zhixue.com/homework_middle_service/stuapp/getStudentHomeWorkList"],
        [
            "https://mhw.zhixue.com/hw/homework/attachment/list",
            "https://mhw.zhixue.com/hwreport/question/getStuReportDetail",
            "https://mhw.zhixue.com/hwreport/student/studentReport",
            "https://mhw.zhixue.com/hw/clock/answer/getClockHomeworkDetail"
        ]
    ]
    urls_exist = [False] * len(urls)
    
    with open(path, "r", encoding = "utf-8") as HAR_file:
        entries = json.loads(HAR_file.read())["log"]["entries"]
    
    for entry in entries:
        request = entry["request"]
        
        for i in range(len(urls)):
            if not urls_exist[i] and any(map(lambda url: request["url"].startswith(url), urls[i])):
                headers[i].clear()
                for item in request["headers"]:
                    headers[i][item["name"]] = item["value"]
                token = headers[i]["sucUserToken"]
                del headers[i]["sucUserToken"]
                if "Authorization" in headers[i]:
                    del headers[i]["Authorization"]
                if i == 1:
                    data = json.loads(request["postData"]["text"])
                    if "userId" in data["base"]:
                        userId = data["base"]["userId"]
                    elif "studentId" in data["params"]:
                        userId = data["params"]["studentId"]
                urls_exist[i] = True
        
        if all(urls_exist) and userId:
            break
    
    else:
        raise AttributeError("HAR 文件缺少数据")

def get(url):
    headers[0].update({"Host": url.split("/")[2], "sucUserToken": token})
    response = requests.get(url, headers = headers[0])
    response.encoding = "utf-8"
    return response.json()

def post(url, data):
    headers[1].update({
        "Host": url.split("/")[2],
        "Origin": f'https://{url.split("/")[2]}',
        "sucUserToken": token,
        "Authorization": token
    })
    response = requests.post(url, headers = headers[1], json = data)
    response.encoding = "utf-8"
    return response.json()

def download(url, path):
    response = requests.get(url, stream = True)
    size = int(response.headers.get("content-length", 0))
    print(f"正在下载：{url}")
    print(f"文件大小：{size / 1024:.2f}KB")
    progress = tqdm(total = size, unit = "B", unit_scale = True)
    with open(path, "wb") as file:
        for data in response.iter_content(chunk_size = 1024):
            progress.update(len(data))
            file.write(data)
    progress.close()

def analyze_homework(homework):
    hwId = homework["hwId"]
    hwType = homework["hwType"]
    stuHwId = homework["stuHwId"]
    file_list = []
    data = {"base": {"appId": "APP"}, "params": {"hwId": hwId, "stuHwId": stuHwId, "studentId": userId}}
    
    if hwType == 102: # 题库作业
        response = post("https://mhw.zhixue.com/hwreport/question/getStuReportDetail", data)
        if "result" in response:
            for question in response["result"]["mainTopics"]:
                content = question["content"] + question["answerHtml"] + question["analysisHtml"]
                file_list += [{"file": {"path": item, "fileType": 1}, "type": "题目"} for item in re.findall('bigger="(.+?)"', content)]
                file_list += [{"file": i, "type": "提交"} for item in question["subTopics"] for i in item["answerResList"]]
    
    elif hwType == 105: # 自由出题
        response = post("https://mhw.zhixue.com/hw/homework/attachment/list", data)
        file_list += [{"file": item, "type": "题目"} for item in response["result"]]
        response = post("https://mhw.zhixue.com/hwreport/question/getStuReportDetail", data)
        if "result" in response:
            file_list += [{"file": item, "type": "答案"} for item in response["result"].get("answerAttachList", [])]
            for question in response["result"]["mainTopics"]:
                file_list += [{"file": i, "type": "提交"} for item in question["subTopics"] for i in item["answerResList"]]
    
    elif hwType == 107: # 打卡任务
        response = post("https://mhw.zhixue.com/hw/clock/answer/getClockHomeworkDetail", data)
        result = response["result"]
        file_list += (
            [{"file": item, "type": "题目"} for item in result.get("hwTopicAttachments", [])] +
            [{"file": item, "type": "答案"} for item in result.get("hwAnswerAttachments", [])] +
            [{"file": item, "type": "答案"} for item in result["hwClockRecordPreviewResponses"][0].get("teacherAnswerAttachments", [])] +
            [{"file": item, "type": "提交"} for item in result["hwClockRecordPreviewResponses"][0].get("answerAttachments", [])]
        )
    
    for file in file_list:
        if not "name" in file["file"]:
            file["file"]["name"] = Path(file["file"]["path"]).name
    file_list = [file for file in file_list if file["file"]["fileType"] != 5] # file type: 1: image, 4: document, 5: text
    return file_list

def main():
    global headers, userId, token
    print("智学网文件下载工具 1.2\n")
    
    # read config
    
    successful = False
    if os.path.exists("zhixue_config.json"):
        try:
            with open("zhixue_config.json", "r", encoding = "utf-8") as config_file:
                config = json.loads(config_file.read())
            headers = config["headers"]
            userId = config["userId"]
            token = config["token"]
            successful = True
            print("读取配置文件成功。")
        except:
            print("读取配置文件失败。")
    
    if not successful:
        print("打开 HAR 文件……")
        dialog = win32ui.CreateFileDialog(1, None, None, win32con.OFN_OVERWRITEPROMPT, "HAR Files (*.har)|*.har||")
        if dialog.DoModal() == win32con.IDOK:
            path = dialog.GetPathName()
            read_HAR_file(path)
            with open("zhixue_config.json", "w", encoding = "utf-8") as config_file:
                config_file.write(json.dumps({"headers": headers, "userId": userId, "token": token}))
            print("更新配置文件成功。")
        else:
            raise ImportError("读取配置文件失败")
    
    # check token
    
    response = get(f"https://www.zhixue.com/container/app/checkToken?token={token}")
    updated = False
    
    while response["errorCode"] != 0:
        print("token 无效或已过期。")
        token = input("请输入 token：\n")
        response = get(f"https://www.zhixue.com/container/app/checkToken?token={token}")
        updated = True
    if updated:
        with open("zhixue_config.json", "w", encoding = "utf-8") as config_file:
            config_file.write(json.dumps({"headers": headers, "userId": userId, "token": token}))
        print("更新配置文件成功。")
    
    # select subjects
    
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
    
    # set homework status and page size
    
    status = input("请输入要获取的作业状态（0 为未完成，1 为已完成，其他为全部）：")
    
    try:
        page_size = int(input("请输入单次请求的作业数量，默认为 20: "))
        if page_size <= 0:
            raise ValueError
    except ValueError:
        page_size = 20
    
    # get homework list
    
    print("获取作业列表中……")
    fetch_list = []
    if status != "1":
        fetch_list += [{"subject": subject, "status": 0} for subject in subjects]
    if status != "0":
        fetch_list += [{"subject": subject, "status": 1} for subject in subjects]
    homework_list = []
    for item in tqdm(fetch_list, unit = ""):
        response = get(f'https://mhw.zhixue.com/homework_middle_service/stuapp/getStudentHomeWorkList?completeStatus={item["status"]}&pageIndex=1&pageSize={page_size}&subjectCode={item["subject"]}&token={token}')
        if response["code"] != 200:
            raise RuntimeError("获取作业列表失败")
        homework_list += response["result"]["list"]
    os.system("cls")
    print("获取作业列表成功。")
    
    # get file list
    
    print()
    for i in range(len(homework_list)):
        print(f'{i + 1}: [{subject_codes[homework_list[i]["subjectCode"]]}] {homework_list[i]["hwTitle"]}')
    print()
    selected_homework = input("请输入要解析的作业编号，以空格分隔：").split()
    selected_homework = [int(i) - 1 for i in selected_homework if i.isdigit() and 0 < int(i) <= len(homework_list)]
    print("解析作业中……")
    file_list = []
    for i in tqdm(selected_homework, unit = ""):
        file_list += analyze_homework(homework_list[i])
    os.system("cls")
    print("解析作业成功。")
    
    # select files
    
    print()
    for i in range(len(file_list)):
        print(f'{i + 1}: [{file_list[i]["type"]}] {file_list[i]["file"]["name"]}')
    print()
    selected_files = input("请输入要下载的文件编号，以空格分隔：").split()
    selected_files = [int(i) - 1 for i in selected_files if i.isdigit() and 0 < int(i) <= len(file_list)]
    batch = False
    if len(selected_files) > 1:
        batch = bool(input("是否批量下载（输入任意字符代表确定，直接按回车键代表取消）："))
    
    if batch:
        dialog = win32ui.CreateFileDialog(0, None, "此处无需填写")
        if dialog.DoModal() == win32con.IDOK:
            path = dialog.GetPathName()
            path = str(Path(path).parent) + "\\"
            for i in selected_files:
                url = file_list[i]["file"]["path"]
                name = file_list[i]["file"]["name"]
                print()
                download(url, path + name)
    
    else:
        for i in selected_files:
            url = file_list[i]["file"]["path"]
            name = file_list[i]["file"]["name"]
            dialog = win32ui.CreateFileDialog(0, None, name)
            if dialog.DoModal() == win32con.IDOK:
                path = dialog.GetPathName()
                print()
                download(url, path)

if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        error_type = str(type(error)).split("'")[1]
        content = str(error)
        print()
        print(f"{error_type}: {content}" if len(content) > 0 else error_type)
    print("\n请按任意键退出……")
    os.system("pause > nul")