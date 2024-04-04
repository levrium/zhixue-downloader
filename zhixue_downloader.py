import json
import os
from pathlib import Path
import time

import requests
from tqdm import tqdm
import win32con
import win32ui

headers = [{}, {}]
data = [{}, {}]
token = ""

def read_HAR_file(path):
    global headers, data, token
    url_1 = "https://mhw.zhixue.com/homework_middle_service/stuapp/getStudentHomeWorkList"
    url_2 = [
        "https://mhw.zhixue.com/hw/homework/attachment/list",
        "https://mhw.zhixue.com/hwreport/question/getStuReportDetail",
        "https://mhw.zhixue.com/hwreport/student/studentReport"
    ]
    url_3 = "https://mhw.zhixue.com/hw/clock/answer/getClockHomeworkDetail"
    urls_exist = [False, False, False]
    
    with open(path, "r", encoding = "utf-8") as file_HAR:
        entries = json.loads(file_HAR.read())["log"]["entries"]
    
    for entry in entries:
        request = entry["request"]
        if not urls_exist[0] and request["url"].startswith(url_1):
            headers[0].clear()
            for i in request["headers"]:
                headers[0][i["name"]] = i["value"]
            token = headers[0]["sucUserToken"]
            del headers[0]["sucUserToken"]
            urls_exist[0] = True
        
        elif not urls_exist[1] and request["url"].split("?")[0] in url_2:
            headers[1].clear()
            for i in request["headers"]:
                headers[1][i["name"]] = i["value"]
            del headers[1]["sucUserToken"], headers[1]["Authorization"]
            data[0] = json.loads(request["postData"]["text"])
            del data[0]["params"]["hwId"], data[0]["params"]["stuHwId"]
            urls_exist[1] = True
        
        elif not urls_exist[2] and request["url"].startswith(url_3):
            data[1] = json.loads(request["postData"]["text"])
            del data[1]["base"]["sucUserToken"], data[1]["params"]["hwId"], data[1]["params"]["stuHwId"]
            urls_exist[2] = True
    
    if not all(urls_exist):
        raise AttributeError("HAR 文件缺少数据")

def get(url):
    headers[0].update({"Host": url.split("/")[2], "sucUserToken": token})
    response = requests.get(url, headers = headers[0])
    response.encoding = "utf-8"
    return response.json()

def post(url, data):
    headers[1].update({
        "Host": url.split("/")[2],
        "Origin": f"https://{url.split("/")[2]}",
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
    
    match hwType:
        case 105: # 自由出题
            data[0]["params"].update({"hwId": hwId, "stuHwId": stuHwId})
            response_1 = post("https://mhw.zhixue.com/hw/homework/attachment/list", data[0])
            response_2 = post("https://mhw.zhixue.com/hwreport/question/getStuReportDetail", data[0])
            file_list += response_1["result"]
            if "result" in response_2:
                file_list += response_2["result"].get("answerAttachList", [])
                for question in response_2["result"]["mainTopics"]:
                    for i in question["subTopics"]:
                        file_list += i["answerResList"]
        
        case 107: # 打卡任务
            data[1]["base"].update({"sucUserToken": token})
            data[1]["params"].update({"hwId": hwId, "stuHwId": stuHwId})
            response = post("https://mhw.zhixue.com/hw/clock/answer/getClockHomeworkDetail", data[1])
            result = response["result"]
            file_list += (
                result.get("hwTopicAttachments", []) +
                result.get("hwAnswerAttachments", []) +
                result["hwClockRecordPreviewResponses"][0].get("teacherAnswerAttachments", []) +
                result["hwClockRecordPreviewResponses"][0].get("answerAttachments", [])
            )
    
    for file in file_list:
        if not "name" in file:
            file["name"] = Path(file["path"]).name
    file_list = list(filter(lambda i: i["fileType"] != 5, file_list)) # file type: 1: image, 4: document, 5: text
    return file_list

def main():
    global headers, data, token
    print("智学网文件下载工具 1.0\n")
    
    # read config
    
    successful = False
    if os.path.exists("zhixue_config.json"):
        try:
            with open("zhixue_config.json", "r", encoding = "utf-8") as file_config:
                config = json.loads(file_config.read())
            headers = config["headers"]
            data = config["data"]
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
            with open("zhixue_config.json", "w", encoding = "utf-8") as file_config:
                file_config.write(json.dumps({"headers": headers, "data": data, "token": token}))
            print("更新配置文件成功。")
        else:
            raise ImportError("读取配置文件失败")
    
    # check token
    
    response = get(f"https://www.zhixue.com/container/app/checkToken?token={token}")
    updated = False
    
    while response["errorCode"] != 0:
        print("token 无效或已过期。")
        token = input("请输入 token：")
        response = get(f"https://www.zhixue.com/container/app/checkToken?token={token}")
        updated = True
    if updated:
        with open("zhixue_config.json", "w", encoding = "utf-8") as file_config:
            file_config.write(json.dumps({"headers": headers, "data": data, "token": token}))
            print("更新配置文件成功。")
    
    # select subjects
    
    response = post("https://mhw.zhixue.com/hw/answer/homework/subjects", data[1])
    subject_codes = []
    print()
    for i in response["result"]:
        subject_codes.append(i["code"])
        print(f"{i["code"]}: {i["name"]}")
    print()
    subjects = input("请输入学科代码，以空格分隔：").split()
    subjects = list(filter(lambda i: i in subject_codes, subjects))
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
    
    homework_list = []
    if status != "1":
        for subject in subjects:
            response = get(f"https://mhw.zhixue.com/homework_middle_service/stuapp/getStudentHomeWorkList?completeStatus=0&pageIndex=1&pageSize={page_size}&subjectCode={subject}&token={token}")
            if response["code"] != 200:
                raise RuntimeError("获取作业列表失败")
            homework_list += response["result"]["list"]
    if status != "0":
        for subject in subjects:
            response = get(f"https://mhw.zhixue.com/homework_middle_service/stuapp/getStudentHomeWorkList?completeStatus=1&pageIndex=1&pageSize={page_size}&subjectCode={subject}&token={token}")
            if response["code"] != 200:
                raise RuntimeError("获取作业列表失败")
            homework_list += response["result"]["list"]
    os.system("cls")
    print("获取作业列表成功。")
    
    # get file list
    
    print()
    for i in range(len(homework_list)):
        print(f"{i + 1}: {homework_list[i]["hwTitle"]}")
    print()
    selected_homework = input("请输入要解析的作业编号，以空格分隔：").split()
    selected_homework = map(lambda i: int(i) - 1, filter(lambda i: i.isdigit(), selected_homework))
    selected_homework = list(filter(lambda i: 0 <= i < len(homework_list), selected_homework))
    file_list = []
    for i in selected_homework:
        file_list += analyze_homework(homework_list[i])
    os.system("cls")
    print("解析作业成功。")
    
    # select files
    
    print()
    for i in range(len(file_list)):
        print(f"{i + 1}: {file_list[i]["name"]}")
    print()
    selected_files = input("请输入要下载的文件编号，以空格分隔：").split()
    selected_files = map(lambda i: int(i) - 1, filter(lambda i: i.isdigit(), selected_files))
    selected_files = list(filter(lambda i: 0 <= i < len(file_list), selected_files))
    batch = False
    if len(selected_files) > 1:
        batch = bool(input("是否批量下载（输入任意字符代表确定，直接按回车键代表取消）："))
    
    if batch:
        dialog = win32ui.CreateFileDialog(0, None, "此处无需填写")
        if dialog.DoModal() == win32con.IDOK:
            path = dialog.GetPathName()
            path = str(Path(path).parent) + "\\"
            for i in selected_files:
                url = file_list[i]["path"]
                name = file_list[i]["name"]
                print()
                download(url, path + name)
    
    else:
        for i in selected_files:
            url = file_list[i]["path"]
            name = file_list[i]["name"]
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