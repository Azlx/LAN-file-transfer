#!/usr/bin/python2
# coding=utf-8
import socket
import sys
import time
import os
import sys

reload(sys)
sys.setdefaultencoding('utf-8')

data_input = sys.argv  # 记录命令行输入内容
bar_length = 20  # 定义进度条长度

# 定义服务端连接函数
def server_socket(close_num=0):
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    host = '0.0.0.0'
    port = 8080
    sock.bind((host, port))

    if close_num == 0:
        sock.listen(5)
        server, address = sock.accept()

        return server, address
    elif close_num == -1:
        sock.close()

# 定义客户端连接函数
def client_socket(host):
    client = socket.socket()

    host = host
    port = 8080
    client.connect((host, port))

    return client

# 定义进度条函数
def progress_bar(total_size, change_size, speed, file_size_MB):
    hashes = '#' * int(float(change_size) / float(total_size) * bar_length)  # 计算已经接收了的进度条长度
    spaces = ' ' * (bar_length - len(hashes))  # 计算剩余进度条长度
    sys.stdout.write(u"\r传输进度: [%s] %d%% 传输速度: %.2fMb/s  文件大小: %.2fMB" % (
        hashes + spaces, float(change_size) / float(total_size) * 100, speed, file_size_MB))

    return sys.stdout.flush()

# 定义计算1S内传输速度函数
def send_speed(sum_send, time_list):
    speed = float(sum_send) / (time_list[-1] - time_list[0]) / 1024 / 1024

    return speed

# 定义接收函数
def recv_data(num=2048000):
    print u'每次接收大小为: {} b'.format(num)
    print u'等待客户端连接中...'
    try:
        server, address = server_socket()
        print u'连接成功,连接的客户端地址为: {}'.format(address)

        # 向客户端发送每次传输大小
        server.send(str(num))

        # 接收文件名
        recv_file_name = server.recv(1024)
        file_name = recv_file_name

        # 成功接收文件名 向客户端发送0
        server.send('0')
        # 接收文件大小
        file_size = server.recv(1024)
        file_size_MB = float(file_size) / 1024 / 1024  # 计算文件的MB

        # 成功接收文件大小 向客户端发送1
        server.send('1')

        # 接收服务端发送的数据
        print u'接收的文件名为: {}'.format(file_name)
        recv_size = 0  # 初始化接收大小
        f = open(file_name, 'wb+')
        loop_size = 0  # 初始化循环变量
        time_list = []  # 初始化计时列表
        speed = 0  # 初始化速度
        sum_send = 0  # 初始化速度变量

        start_time = time.time()  # 记录接收开始时间
        while True:
            # 接收数据
            try:
                recv = server.recv(num)
                recv_size += len(recv)  # 记录接收的大小
                loop_size += len(recv)

                # 记录接收时间
                send_time = time.time()
                time_list.append(send_time)

                # 判断是否接收成功 接收成功则向客户端发送1
                if loop_size >= num:
                    server.send('1')
                    loop_size -= num

                    # 计算接收速度
                    sum_send += num
                    if time_list[-1] - time_list[0] >= 1:
                        speed = send_speed(sum_send, time_list)
                        time_list = time_list[-1:]
                        sum_send = 0

                    # 设置进度条
                    progress_bar(file_size, recv_size, speed, file_size_MB)

                f.write(recv)
                # 判断客户端是否断开链接
                if time_list[-1] - time_list[0] >= 5:
                    recv_num = 2
                    server.close()
                    f.close()
                    break

                # 判断是否接收完成
                if recv_size == float(file_size):
                    # 记录接收时间
                    send_time = time.time()
                    time_list.append(send_time)
                    # 计算接收速度
                    sum_send += num
                    if time_list[-1] - time_list[0] >= 1:
                        speed = send_speed(sum_send, time_list)
                        time_list = time_list[-1:]
                        sum_send = 0
                    # 设置进度条
                    progress_bar(file_size, recv_size, speed, file_size_MB)

                    server.send('5')
                    recv_num = 1
                    break
                elif recv_size > float(file_size):
                    recv_num = -1
                    break
            except socket.error:
                print u'\n客户端断开！'
                recv_num = 0
                f.close()
                break
            except KeyboardInterrupt:
                print u'\n取消接收!'
                recv_num = 0
                f.close()
                break
        end_time = time.time()  # 记录接收结束时间
        # 判断传输结果
        if recv_num == 1:
            print u'\n接收成功, 用时{:.2f}s'.format(end_time - start_time)
            f.close()
            server.close()
        elif recv_num == -1:
            print u'\n接收出错！'
            f.close()
            server.close()
        elif recv_num == 0:
            server_socket(-1)
        elif recv_num == 2:
            print u'\n客户端断开！'
    except ValueError:
        print u'客户端发送文件出错！'
    except:
        print u'\b\b取消接收！'

# 定义发送函数
def send_data():
    try:
        client = client_socket(data_input[2])

        # 接收每次传输大小
        num = int(client.recv(1024))

        if num >= 1024 and num <= 2048000:
            # 向服务端发送文件名
            file_name = data_input[1]

        f = open(file_name, 'rb')
        client.send(file_name)
        print u'服务器可接受的每次传输大小为: {} b'.format(num)
        print u'发送的文件名为: {}'.format(file_name)

        # 接收服务端接收文件名的返回值
        name_num = client.recv(1)
        if name_num == '0':
            # 文件名返回值正确 向服务端发送文件大小
            file_size = os.path.getsize(file_name)
            file_size_MB = float(file_size) / 1024 / 1024  # 计算文件的MB
            client.send(str(file_size))
            remain_size = file_size  # 初始化传输文件的剩余大小

        else:
            print u'传输文件名出错'

        # 向向服务器发送数据
        time_list = []  # 初始化计时列表
        speed = 0  # 初始化速度
        sum_send = 0  # 初始化速度变量
        # 异常处理
        try:
            start_time = time.time()  # 记录发送开始时间
            while True:
                cycle_num = client.recv(1)  # 接收服务端的返回值
                # 判断服务端的返回值
                if cycle_num == '1':
                    str_content = f.read(num)
                    client.sendall(str_content)
                    remain_size -= num

                    # 记录传输时间
                    send_time = time.time()
                    time_list.append(send_time)
                    # 计算传输速度
                    sum_send += num
                    if time_list[-1] - time_list[0] >= 1:
                        speed = send_speed(sum_send, time_list)
                        time_list = time_list[-1:]
                        sum_send = 0
                    # 设置进度条
                    progress_bar(file_size, file_size - remain_size, speed, file_size_MB)

                elif cycle_num == '5':
                    send_sum = 1
                    break
                else:
                    send_sum = -1
                    break
            end_time = time.time()  # 记录发送结束时间
            f.close()
            # 判断传输结果
            if send_sum == 1:
                print u'\n传输完成,共用时{:.2f}s'.format(end_time - start_time)
            elif send_sum == -1:
                print u'\n服务端断开!'
            else:
                print u'\n未知错误'
        except socket.error as reason:
            print u'\n服务端断开!'
            f.close()
    except socket.error:
        print u'服务器尚未打开或服务器地址输入有误,请重试!'
    except IOError:
        print u'文件不存在!'

if len(data_input) <= 2:  # 判断服务端输入方式
    if len(data_input) == 2:
        try:
            recv_size = int(data_input[1])
            if recv_size == 3 :
                num = 1024000
                recv_data(num)
            elif recv_size == 2 :
                num = 512000
                recv_data(num)
            elif recv_size == 1 :
                num = 102400
                recv_data(num)
            elif recv_size == 0 :
                num = 10240
                recv_data(num)
            else:
                print u'每次接收大小的参数输入错误,请输入0-3的任意整数!\n' \
                      u'0: 10240 b\n' \
                      u'1: 102400 b\n' \
                      u'2: 512000 b\n' \
                      u'3: 1024000 b\n'
        except ValueError:
            print u'输入错误！'
    else:
        recv_data()
elif len(data_input) == 3:  # 判断客户端输入方式
    try:
        send_data()
    except KeyboardInterrupt:
        print u'\n取消发送!'
elif len(data_input) > 3:
    print u'输入错误!'
