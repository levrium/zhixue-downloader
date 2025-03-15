# 智学网文件下载器

[Github 仓库](https://github.com/levrium/zhixue-downloader)

[下载链接](https://www.alipan.com/s/rSHHVoMKDRU)

## 功能介绍

目前支持下载题库作业、自由出题、习惯练习中题目、答案、提交的图片、音频、视频、文档。

本工具的特殊功能：

- 下载题库作业内题目中部分图片的高清版本
- 下载过期的自由出题、习惯练习的答案
- 在习惯练习的提交无法预览时仍可正常下载

## 运行环境

操作系统：Windows

Python 版本：3.6+

需安装的第三方库：`requests`、`tqdm`

也可以下载打包好的 exe 文件，可以直接运行。

## 使用说明

- **请勿使用 Python 自带的 IDLE 运行本程序。可以直接双击运行或用命令行切换至程序所在目录后输入 `python zhixue_downloader.py` 或 `zhixue_downloader.exe` 运行。**

- 程序所在目录下会生成一个名为 `zhixue_config.json` 的文件。**这是程序生成的配置文件，请勿随意修改或删除。**

运行程序后按照程序提示操作即可。

**对于所有需回答“是”或“否”的问题，输入任意字符代表是，直接按回车键代表否。**

若程序提示输入 cookie，按照以下步骤操作：

1. 打开[智学网](https://www.zhixue.com/)并**登录**。
2. 打开浏览器开发者工具，找到该网站的 cookie。本程序需要其中的 `ui` 和 `tlsysSessionId` 的值。

### 额外说明

单次请求的作业数量：单个学科（“全部”视为一个学科）、单种状态（未完成/已完成）的作业数量。

批量下载：将所有文件下载至同一个文件夹，此时无法在程序内对每个文件进行重命名，但可以批量重命名为连续编号。

## 更新日志

V2.0：

- 简化了操作流程，现在不需要在手机上抓包。
- 现在可以下载作业说明和提交的文本。
- 现在会显示作业的起止时间。
- 作业列表可以选择继续加载。
- 输入编号时可以输入范围。
- 使用双线程分别询问保存路径和下载文件。
- 批量下载时可以将文件重命名为连续编号。
- 批量下载时遇到同名文件会自动重命名。
- 程序结束后可以选择重启。
- 用 `tkinter` 替代了 `pywin32` 模块。
- 显示的错误信息更丰富了。
- 修复了文件名含有非法字符导致保存失败的问题。

V1.3：增加对题库作业的支持。

V1.2：降低 Python 版本要求；增加作业学科和文件来源标注；增加获取作业列表和解析作业的进度条。

V1.1：优化初次使用流程。

V1.0：首次发布。