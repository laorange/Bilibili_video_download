# !/usr/bin/python
# -*- coding:utf-8 -*-
# time: 2019/07/02--08:12
# __author__ = 'Henry'

# edit time: 2021-08-29
#

"""
项目: B站视频下载 - GUI版本
版本1: 加密API版,不需要加入cookie,直接即可下载1080p视频
20190422 - 增加多P视频单独下载其中一集的功能
20190702 - 增加视频多线程下载 速度大幅提升
20190711 - 增加GUI版本,可视化界面,操作更加友好

20210828 - 修复b站接口更换带来的bug & 优化UI  【edit by Github@laorange】
"""

import requests
import time
import hashlib
import urllib.request
import re
# import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import StringVar

# from moviepy.editor import VideoFileClip, concatenate_videoclips

downloaded_num = 0
total_amount = 0


def initialize():
    global downloaded_num, total_amount
    downloaded_num = total_amount = 0
    confirm['state'] = tk.NORMAL


def base_path(path):
    if getattr(sys, 'frozen', None):
        basedir = sys._MEIPASS
    else:
        basedir = os.path.dirname(__file__)
    return os.path.join(basedir, path)


BASE_PATH = base_path("")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'download')  # 下载目录
# 创建文件夹存放下载的视频
if not os.path.exists(OUTPUT_PATH):
    os.makedirs(OUTPUT_PATH)

root = tk.Tk()
start_time = time.time()


# 将输出重定向到表格
def print_diy(text, print_time=True):
    time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    output = text + '\n'
    if print_time:
        output = time_now + "：" + output
    msgbox.insert(tk.END, output)
    msgbox.see(tk.END)


# 访问API地址
def get_play_list(start_url, cid, quality):
    entropy = 'rbMCKn@KuamXWlPMoJGsKcbiJKUfkPF_8dABscJntvqhRSETg'
    appkey, sec = ''.join([chr(ord(i) + 2) for i in entropy[::-1]]).split(':')
    params = 'appkey=%s&cid=%s&otype=json&qn=%s&quality=%s&type=' % (appkey, cid, quality, quality)
    chksum = hashlib.md5(bytes(params + sec, 'utf8')).hexdigest()
    url_api = 'https://interface.bilibili.com/v2/playurl?%s&sign=%s' % (params, chksum)
    headers = {
        'Referer': start_url,  # 注意加上referer
        # 'Cookie': '',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'
    }
    # print(url_api)
    html = requests.get(url_api, headers=headers).json()
    # print(json.dumps(html))
    video_list = []
    for i in html['durl']:
        video_list.append(i['url'])
    # print(video_list)
    return video_list


# 下载视频
'''
 urllib.urlretrieve 的回调函数：
def callbackfunc(blocknum, blocksize, totalsize):
    @blocknum:  已经下载的数据块
    @blocksize: 数据块的大小
    @totalsize: 远程文件的大小
'''


def process_for_one_page(blocknum, blocksize, totalsize):
    speed = (blocknum * blocksize) / (time.time() - start_time)
    # speed_str = " Speed: %.2f" % speed
    speed_str = "{}/s".format(format_size(speed))
    recv_size = blocknum * blocksize

    # 设置下载进度条
    percent = recv_size / totalsize
    if percent >= 1:
        percent = 1
        initialize()
    percent_str = "%.2f%%" % (percent * 100)

    download.coords(fill_line1, (0, 0, percent * 465, 23))
    root.update()
    pct.set(percent_str + " " + speed_str)


def process_for_several_pages(blocknum, blocksize, totalsize):
    global downloaded_num
    threading_num = len(threading.enumerate())
    speed = (blocknum * blocksize) / (time.time() - start_time) * (threading_num - normal_threading_num)
    # speed_str = " Speed: %.2f" % speed
    speed_str = "{}/s".format(format_size(speed))
    # print(threading_num - normal_threading_num, speed_str)

    recv_size = blocknum * blocksize
    # 设置下载进度条
    percent = recv_size / totalsize
    percent = percent if percent < 1 else 1
    if (blocknum + 1) * blocksize >= totalsize:
        if blocknum * blocksize < totalsize:
            downloaded_num += 1

    total_percentage = (downloaded_num + percent) / total_amount if downloaded_num != total_amount else 1
    if total_percentage == 1:
        initialize()

    percent_str = "%.2f%%" % (total_percentage * 100)

    download.coords(fill_line1, (0, 0, total_percentage * 465, 23))
    root.update()
    pct.set(percent_str + " " + speed_str)


# 字节bytes转化K\M\G
def format_size(bytes):
    try:
        bytes = float(bytes)
        kb = bytes / 1024
    except:
        print_diy("传入的字节格式不对")
        return "Error"
    if kb >= 1024:
        M = kb / 1024
        if M >= 1024:
            G = M / 1024
            return "%.3f G" % G
        else:
            return "%.3f M" % M
    else:
        return "%.3f kb" % kb


#  下载视频
def down_video(video_list, title, start_url, page, video_format="flv"):
    num = 1
    print_diy('[正在下载P{}段视频,请稍等...]:'.format(page) + title)
    currentVideoPath = os.path.join(OUTPUT_PATH, title)  # 当前目录作为下载目录
    for i in video_list:
        opener = urllib.request.build_opener()
        # 请求头
        opener.addheaders = [
            # ('Host', 'upos-hz-mirrorks3.acgvideo.com'),  # 注意修改host,不用也行
            ('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:56.0) Gecko/20100101 Firefox/56.0'),
            ('Accept', '*/*'),
            ('Accept-Language', 'en-US,en;q=0.5'),
            ('Accept-Encoding', 'gzip, deflate, br'),
            ('Range', 'bytes=0-'),  # Range 的值要为 bytes=0- 才能下载完整视频
            ('Referer', start_url),  # 注意修改referer,必须要加的!
            ('Origin', 'https://www.bilibili.com'),
            ('Connection', 'keep-alive'),
        ]
        urllib.request.install_opener(opener)
        # 创建文件夹存放下载的视频
        if not os.path.exists(currentVideoPath):
            os.makedirs(currentVideoPath)
        # 开始下载
        if total_amount > 1:
            reporthook_func = process_for_several_pages
        else:
            reporthook_func = process_for_one_page
        if len(video_list) > 1:
            urllib.request.urlretrieve(url=i, filename=os.path.join(currentVideoPath,
                                                                    r'{}-{}.{}'.format(title, num, video_format)),
                                       reporthook=reporthook_func)

        else:
            urllib.request.urlretrieve(url=i,
                                       filename=os.path.join(currentVideoPath, r'{}.{}'.format(title, video_format)),
                                       reporthook=reporthook_func)  # 写成mp4也行  title + '-' + num + '.flv'
        num += 1


def start_a_thread(ths: list[threading.Thread]):
    # 开始线程
    for th in ths:
        th.start()
    # 等待所有线程运行完毕
    for th in ths:
        th.join()


def do_prepare(inputStart, inputQuality, simultaneous_num: int = 5, video_format="flv"):
    global OUTPUT_PATH, total_amount
    confirm['state'] = tk.DISABLED
    try:
        # 清空进度条
        download.coords(fill_line1, (0, 0, 0, 23))
        pct.set('0.00%')
        root.update()

        # 清空文本栏
        # msgbox.delete('1.0', 'end')

        start_time = time.time()
        # 用户输入av号或者视频链接地址
        print_diy("\n\n" + '*' * 30 + 'B站视频-下载小助手' + '*' * 30, print_time=False)
        start = inputStart
        if bv_search := re.search(r'/?(BV\w+)/?', start):
            start_url = "https://api.bilibili.com/x/web-interface/view?bvid=" + bv_search.group(1)
        elif av_search := re.search(r'/(av\d+)/?', start):
            start_url = "https://api.bilibili.com/x/web-interface/view?aid=" + av_search.group(1)
        else:
            initialize()
            raise Exception("解析错误。请检查输入的网址是否正确。")

        # 视频质量
        # <accept_format><![CDATA[flv,flv720,flv480,flv360]]></accept_format>
        # <accept_description><![CDATA[高清 1080P,高清 720P,清晰 480P,流畅 360P]]></accept_description>
        # <accept_quality><![CDATA[80,64,32,16]]></accept_quality>
        quality = inputQuality
        # 获取视频的cid,title
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'
        }
        html = requests.get(start_url, headers=headers).json()
        data = html['data']
        cid_list = []
        if '?p=' in start:
            # 单独下载分P视频中的一集
            p = re.search(r'\?p=(\d+)', start).group(1)
            cid_list.append(data['pages'][int(p) - 1])
        else:
            # 如果p不存在就是全集下载
            cid_list = data['pages']

        total_amount += len(cid_list)

        if total_amount > 1:

            OUTPUT_PATH = os.path.join(OUTPUT_PATH, data['title'])
            if not os.path.exists(OUTPUT_PATH):
                os.makedirs(OUTPUT_PATH)

        # 创建线程池
        threadpool = []
        title_list = []
        for item in cid_list:
            cid = str(item['cid'])
            title = item['part']
            title = re.sub(r'[/\\:*?"<>|]', '', title)  # 替换为空的
            print_diy('[下载视频的cid]:' + cid)
            print_diy('[下载视频的标题]:' + title)
            title_list.append(title)
            page = str(item['page'])
            start_url = start_url + "/?p=" + page
            video_list = get_play_list(start_url, cid, quality)
            start_time = time.time()
            # 定义线程
            th = threading.Thread(target=down_video, args=(video_list, title, start_url, page, video_format))
            # 将线程加入线程池
            threadpool.append(th)
        index_num = 0
        thread_amount = len(threadpool)
        while index_num < thread_amount:
            if index_num + simultaneous_num >= thread_amount:
                start_a_thread(threadpool[index_num:thread_amount])
            else:
                start_a_thread(threadpool[index_num:index_num + simultaneous_num])
            index_num += simultaneous_num

        end_time = time.time()  # 结束时间
        print_diy('下载总耗时%.2f秒,约%.2f分钟' % (end_time - start_time, int(end_time - start_time) / 60))

        # 如果是windows系统，下载完成后打开下载目录
        if sys.platform.startswith('win'):
            os.startfile(OUTPUT_PATH)
    except Exception as e:
        print_diy(str(e))


def thread_it(func, *args):
    """将函数打包进线程"""
    # 创建
    t = threading.Thread(target=func, args=args)
    # 守护 !!!
    t.setDaemon(True)
    # 启动
    t.start()


if __name__ == "__main__":
    # 设置标题
    root.title('B站视频-下载小助手')
    # 设置ico
    root.iconbitmap(os.path.join(BASE_PATH, 'favicon.ico'))
    # 设置Logo
    photo = tk.PhotoImage(file=os.path.join(BASE_PATH, 'logo.png'))
    logo = tk.Label(root, image=photo)
    logo.pack()
    # 各项输入栏和选择框
    inputStart = tk.Entry(root, bd=5, width=465, highlightcolor="#FF0000")
    labelStart = tk.Label(root, text="👇 请输入您要下载的B站视频链接:", font=12, justify=tk.CENTER, pady=10)
    labelStart.pack(anchor="w", )
    inputStart.pack()

    labelQual = tk.Label(root, text="\n请选择您要下载视频的清晰度:")  # 清晰度选择
    labelQual.pack(anchor="w")
    inputQual = ttk.Combobox(root, state="readonly")
    # 可供选择的表
    inputQual['value'] = ('1080P', '720p', '480p', '360p')
    keyTrans = dict()  # 对应的转换字典
    keyTrans['1080P'] = '80'
    keyTrans['720p'] = '64'
    keyTrans['480p'] = '32'
    keyTrans['360p'] = '16'
    inputQual.current(1)  # 初始值为720p
    inputQual.pack()

    mp4_flv_input_label = tk.Label(root, text="\n请选择您要下载视频的格式:")  # 视频格式选择
    mp4_flv_input_label.pack(anchor="w")
    mp4_flv_input = ttk.Combobox(root, state="readonly")
    mp4_flv_input['value'] = ('mp4', 'flv')
    mp4_flv_input.current(0)
    mp4_flv_input.pack()
    mp4_flv_dict = {'mp4': "mp4", "flv": "flv"}

    simultaneous_num_label = tk.Label(root, text="\n请选择同时下载的视频个数:")  # 视频格式选择
    simultaneous_num_label.pack(anchor="w")
    simultaneous_num_input = ttk.Combobox(root, state="readonly")
    simultaneous_num_input['value'] = [str(i) for i in range(1, 10)]
    simultaneous_num_input.current(4)
    simultaneous_num_input.pack()

    confirm = tk.Button(root, text="开始下载",
                        command=lambda: thread_it(do_prepare, inputStart.get(),
                                                  keyTrans[inputQual.get()],
                                                  int(simultaneous_num_input.get()),
                                                  mp4_flv_dict[mp4_flv_input.get()]))

    download = tk.Canvas(root, width=465, height=15, bg="white")
    # 进度条的设置
    labelDownload = tk.Label(root, text="下载进度")
    labelDownload.pack(anchor="w")
    download.pack()
    fill_line1 = download.create_rectangle(0, 0, 0, 15, width=0, fill="green")
    pct = StringVar()
    pct.set('0.0%')
    pctLabel = tk.Label(root, textvariable=pct)
    pctLabel.pack()
    root.geometry("720x700+400+50")
    confirm.pack()

    msgbox = tk.Text(root, height=50, width=200)
    msgbox.insert('1.0',
                  "💡 对于单P视频:直接传入视频链接地址\n    例：https://www.bilibili.com/video/BV1UL411t7CR\n\n\n"
                  "💡 对于多P视频:\n    1.下载全集:直接传入B站视频链接地址，例：https://www.bilibili.com/video/BV11K411376D\n"
                  "    2.下载其中一集:传入那一集的视频链接地址，例：https://www.bilibili.com/video/BV11K411376D?p=8\n\n"
                  "该程序仅用于学习交流，请勿用于任何商业用途！谢谢\n")

    scroll = tk.Scrollbar()
    # 放到窗口的右侧, 填充Y竖直方向
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    # 两个控件关联
    scroll.config(command=msgbox.yview)
    msgbox.config(yscrollcommand=scroll.set)
    msgbox.pack()

    inputStart.insert(0, " ")  # 美化输入框
    inputStart.focus()  # 获取焦点

    normal_threading_num = len(threading.enumerate()) + 1

    # GUI主循环
    root.mainloop()
