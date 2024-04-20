# 智学网文件下载工具

[Github 仓库](https://github.com/limouvre/zhixue-downloader)

[下载链接](https://www.alipan.com/s/rSHHVoMKDRU)

## 更新日志

V1.1：优化初次使用流程。

V1.0：首次发布。

## 功能介绍

目前支持下载自由出题、打卡任务中题目、答案、提交的图片、音频、视频、文档。

本工具的特殊功能：

- 下载过期的自由出题/打卡任务的答案
- 在打卡作业的提交无法预览时仍可正常下载

由于能力有限无法模拟登录，每次使用间隔超过 24 小时需要重新手动获取 token。

## 准备工作

### 安装抓包软件

需要在手机上安装抓包软件。可以参考以下文章：

[如何在 Android 手机上实现抓包？](https://www.zhihu.com/question/20467503/answer/19540711)

[Android 抓包工具——HttpCanary](https://cloud.tencent.com/developer/article/1858095)

[IOS免费抓包神器——Stream](https://blog.csdn.net/weixin_44504146/article/details/121946958)

### 运行环境

操作系统：Windows

Python 版本：3.12+

需安装的第三方库：`pywin32`、`requests`、`tqdm`

也可以下载打包好的 exe 文件，可以直接运行。

## 初次使用

请按以下步骤操作：

1. 打开智学网学生端，但不要进行任何操作；
2. 开始抓包；
3. 刷新一次作业列表；
4. 点进任意一个作业；
5. 结束抓包，将所有记录保存为 HAR 文件；
6. 运行程序，按提示上传文件。

若成功，程序所在目录下会生成一个名为 `zhixue_config.json` 的文件。**这是程序生成的配置文件，请勿随意修改或删除。**

## 使用说明

**请勿使用 Python 自带的 IDLE 运行本程序。可以直接双击运行或用命令行切换至程序所在目录后输入 `python zhixue_downloader.py` 或 `zhixue_downloader.exe` 运行。**

运行程序后按照程序提示操作即可。

若距上一次更新 token 超过 24 小时，需要重新获取 token，步骤如下：

1. 打开智学网学生端，但不要进行任何操作；
2. 开始抓包；
3. 刷新一次作业列表；
4. 结束抓包，在抓包软件内查看记录，找到对以下链接的请求（忽略链接中 `?` 及以后的部分）：\
    `https://mhw.zhixue.com/homework_middle_service/stuapp/getStudentHomeWorkList`
5. 在**请求头部**找到 `sucUserToken` 字段，复制它的值；
6. 运行程序，按提示输入 token。

注：手机与电脑间可使用 [note.ms](https://note.ms/) 等网络剪贴板进行文本互传。

### 一些短语的说明

单次请求的作业数量：单个学科（“全部”视为一个学科）、单种状态（未完成/已完成）的作业数量。

批量下载：将所有文件下载至同一个文件夹，此时无法在程序内进行重命名。