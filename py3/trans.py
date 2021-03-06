import os
import sys
import time
import json
import socket
import shutil
import zipfile
import argparse

from pathlib import Path

# 进度条长度
BAR_LENGTH = 20

# 接收文件的位置
RECEIVE_DIR = ''

# 传输文件出错列表
TRANS_ERROR_LIST = []


def set_argparse():
    """
    设置运行脚本参数
    :return:
    """
    # RawDescriptionHelpFormatter参数指定description直接输出原始形式(不进行自动换行和消除空白的操作)
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.description = \
        '传输文件脚本。\n' \
        '说明: 服务端为文件的接收者，客户端为文件的发送者。\n' \
        '使用方法：\n\t' \
        '先在一台机器上启动服务端, 示例命令: python trans.py server {optional}  ' \
        '可选则使用"-p"和"-m"参数\n\t' \
        '然后在另外一台机器上启动客户端, 示例命令: python trans.py client {optional}  ' \
        '必须指定"-a","-P"参数,可选择使用"-p"参数'

    parser.add_argument('type', help='server or client', type=str,
                        choices=['server', 'client'])
    parser.add_argument('-a', '--address', help='连接地址')
    parser.add_argument('-m', '--Mbps',
                        help='每次传输的数据包大小, 单位: Mbps, default=1Mbps. '
                             '注意：此选项的大小取决于网络带宽，设置过大可能会导致传输失败',
                        type=float)
    parser.add_argument('-p', '--port', help='端口, default=8080', type=int)
    parser.add_argument('-P', '--path', help='传输文件路径')
    parser.add_argument('-z', '--zip', action='store_true', help='是否进行压缩传输, 默认为否; 不需要参数，如需压缩传输加上 -z 即可')

    return parser.parse_args()


def get_socket_connection(host='0.0.0.0', port='8800', conn_type='server'):
    """
    获取 socket 连接
    :param host: 连接地址
    :param port: 端口
    :param conn_type: 连接类型，默认为server, 可选值[server, client]
    :return:
    """
    socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if conn_type == 'server':
        # 设置端口复用
        socket_obj.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        socket_obj.bind((host, port))
        socket_obj.listen(5)

        return socket_obj.accept()
    elif conn_type == 'client':
        socket_obj.connect((host, port))

        return socket_obj
    else:
        raise ValueError('conn_type 可取值列表：[server, client]')


def progress_bar(file_size, change_size, speed, fix_show_bar=False):
    """
    传输进度条
    实现方法：在同一行循环打印进度条， 使用字符串 "-r" 方法没每次打印时定位到开始位置
    :param file_size: 传输文件的大小
    :param change_size: 已经传输的大小
    :param speed: 传输速度
    :param fix_show_bar: 后一次打印的长度小于前一次的话，会有前一次的部分内容显示出来，
                         使用此参数多加几个空格完全覆盖前一次的内容
    :return:
    """
    # 计算已接收的进度条长度
    received = '#' * int(float(change_size) / float(file_size) * BAR_LENGTH)

    # 计算未接收的进度条长度
    leftover = ' ' * (BAR_LENGTH - len(received))

    complete = received + leftover
    percentage = float(change_size) / float(file_size) * 100

    # 小文件传输bug修正
    if len(complete) > 20:
        complete = '#' * 20

    if percentage > 100:
        percentage = 100

    format_file_size, format_file_size_unit = format_unit(file_size)
    file_size = '{0:.2f} {1}'.format(format_file_size, format_file_size_unit)

    show_style = '\r\t传输进度: [{0}] {1:.2f}%  传输速度: {2}  文件大小: {3}          '.\
        format(complete, percentage, speed, file_size)

    sys.stdout.write(show_style if not fix_show_bar else show_style + ' ' * 10)

    return sys.stdout.flush()


def format_unit(size):
    """
    格式话单位
    :param size:
    :return:
    """
    if size < 1024:
        unit = 'b'
    elif 1024 <= size < 1024 ** 2:
        size = float(size) / 1024
        unit = 'kb'
    elif 1024 ** 2 <= size < 1024 ** 3:
        size = float(size) / 1024 ** 2
        unit = 'Mb'
    else:
        size = float(size) / 1024 ** 3
        unit = 'Gb'

    return size, unit


def get_speed(total_size, time_list):
    """
    计算传输速度
    :param total_size:  传输大小
    :param time_list: 时间列表
    :return:
    """
    size, unit = format_unit(total_size)
    speed = float(size) / (time_list[-1] - time_list[0])

    return '{0:.2f} {1}/s'.format(speed, unit)


def get_ipv4_address():
    """
    获取本机所有绑定的 ipv4 地址
    :return:
    """
    all_address = socket.getaddrinfo(socket.gethostname(), None)
    ipv4_list = [i[4][0] for i in all_address if ':' not in i[4][0]]

    # 列表去重，及去除 '127.0.0.1'
    ipv4_list = list(set(ipv4_list))
    if '127.0.0.1' in ipv4_list:
        ipv4_list.remove('127.0.0.1')

    return ipv4_list


def get_files_list(dir_path, files=None):
    """
    获取指定目录的文件列表
    :param dir_path: 目录路径
    :param files: 返回值
    :return:
    """
    dir_path = Path(dir_path)
    if not dir_path.exists():
        raise FileNotFoundError('该 {0} 目录或文件不存在'.format(dir_path))

    files = files if files else []
    if dir_path.is_dir():
        for path_obj in dir_path.iterdir():
            if path_obj.name == '.DS_Store':
                continue

            if path_obj.is_dir():
                get_files_list(str(path_obj), files=files)
            else:
                files.append(str(path_obj))
    else:
        files.append(str(dir_path))

    return files


def zip_files(src_path, dst_dir):
    """
    压缩文件方法
    :param src_path: 要压缩的路径
    :param dst_dir: 压缩文件保存的路径
    :return:
    """
    dst_path = Path(dst_dir) / '{0}.zip'.format(Path(src_path).name)
    z = zipfile.ZipFile(str(dst_path), 'w', zipfile.ZIP_DEFLATED)

    files_list = get_files_list(src_path)
    for zip_file in files_list:
        file_relative_path = \
            zip_file.split(src_path)[-1] if zip_file.split(src_path)[-1] else Path(zip_file).name
        print('\t-- 压缩 {0} 文件'.format(file_relative_path))
        z.write(zip_file, file_relative_path)

    z.close()

    return dst_path


def unzip_files(zip_file_path):
    """
    解压指定压缩文件
    :param zip_file_path: 压缩文件，Type: Path Class
    :return:
    """
    dst_path = Path(RECEIVE_DIR) / zip_file_path.name.split('.zip')[0]

    z = zipfile.ZipFile(str(zip_file_path), 'r')
    z.extractall(dst_path)
    z.close()

    return dst_path


def print_msg(trans_type, trans_info, trans_size):
    """
    打印当前的传输信息
    :param trans_type:
    :param trans_info:
    :param trans_size:
    :return:
    """
    new_trans_size, new_trans_size_unit = format_unit(trans_size)
    new_file_size, new_file_size_unit = format_unit(trans_info['file_info']['file_size'])
    print('\n当前{0}第{1}个文件，总共{2}个:\n\t文件名：{3}, 文件大小：{4:.2f}{5}, 每次传输的大小：{6:.2f}{7}'.format(
        '传输' if trans_type == 'send' else '接收',
        trans_info['current_number'],
        trans_info['total_files'],
        trans_info['file_info']['file_name'],
        new_file_size,
        new_file_size_unit,
        new_trans_size,
        new_trans_size_unit
    ))


def trans_server(trans_size, port):
    """
    服务端接收文件方法
    :param trans_size: 服务端每次可接收文件的大小
    :param port: 服务端端口
    :return:
    """
    ipv4s = get_ipv4_address()
    print('服务端启动成功，获取到服务端所有的ipv4地址为：')
    for ip in ipv4s:
        print('\t-- {0}'.format(ip))

    print('\n等待客户端连接中...')
    server, address = get_socket_connection(port=port)
    print('\t客户端({0}:{1})连接成功!'.format(address[0], address[-1]))

    # 向客户端发送服务端每次能接收文件的大小
    print('\n开始准备传输前的数据：')
    server.send(str(trans_size).encode())
    print('\t传输前数据准备完毕，开始接收文件!')

    receive_start_time = time.time()

    while True:
        # 接收客户端传送的信息
        trans_info = json.loads(server.recv(2048).decode())

        # 向客户端传递 1，表示可以传输文件
        server.send('1'.encode())

        save_path = Path(RECEIVE_DIR) / trans_info['file_info']['file_relative_path']

        receive_file(server, trans_info, trans_size, save_path)

        if trans_info['use_zip']:
            print('\n\n压缩传输, 开始解压文件：\n\t-- 解压 {0}'.format(str(save_path.absolute())))
            dst_path = unzip_files(save_path)
            print('\n文件解压完成，解压后文件路径为：\n\t-- {0}\n'.format(str(dst_path.absolute())))

            print('开始清理压缩文件：\n\t-- 清理 {0}'.format(str(save_path.absolute())))
            save_path.unlink()
            print('\n压缩文件清理完毕！\n'.format(str(save_path.absolute())))

        # 判断是否是传输的最后一个文件
        if trans_info['total_files'] - trans_info['current_number'] == 0:
            break

    server.close()

    global TRANS_ERROR_LIST
    receive_end_time = time.time()
    print('\n全部接收完毕，共 {0} 个文件，成功 {1} 个， 失败 {2} 个， 共用时 {3:.2f} s'.format(
        trans_info['total_files'],
        int(trans_info['total_files']) - len(TRANS_ERROR_LIST),
        len(TRANS_ERROR_LIST),
        receive_end_time - receive_start_time
    ))

    if TRANS_ERROR_LIST:
        for error_file in TRANS_ERROR_LIST:
            print('\n接收失败文件名：{0}, 失败原因：{1}'.format(
                error_file['file_name'],
                error_file['error_msg']
            ))

    sys.exit()


def receive_file(server, trans_info, trans_size, save_path):
    """
    接收文件方法
    :param server: 服务端连接
    :param trans_info: 传输信息
    :param trans_size: 每次传输文件的大小
    :param save_path: 接收文件的保存路径，类型：Path Class
    :return:
    """
    file_name = trans_info['file_info']['file_name']
    file_size = trans_info['file_info']['file_size']

    print_msg('receive', trans_info, trans_size)

    # 判断接收文件的父目录是否已经创建
    if not save_path.parent.exists():
        save_path.parent.mkdir(parents=True)

    f = open(str(save_path.absolute()), 'wb+')

    # 已接收大小
    received_size = 0
    # 每次循环接收的大小
    receive_loop_size = 0
    # 每秒接收的大小
    received_second = 0
    # 每次接收的时间列表
    received_times = []
    # 首次接收到空字符换串时记录的时间
    received_null_time = ''

    start_time = time.time()
    while True:
        received = server.recv(int(trans_size))

        # 记录接收时间
        received_times.append(time.time())

        # 记录本次接收大小
        received_size += len(received)
        receive_loop_size += len(received)
        received_second += len(received)

        # 写入本次接收的内容
        f.write(received)

        # 计算接收速度并设置进度条(1s 计算一次)
        if received_times[-1] - received_times[0] >= 1:
            speed = get_speed(received_second, received_times)

            # 设置进度条
            progress_bar(file_size, received_size, speed)

            received_second = 0
            received_times = received_times[-1:]

        # 判断客户端单次发送的数据是否已全部接收完
        if receive_loop_size >= trans_size:
            receive_loop_size = 0
            server.send('1'.encode())
        else:
            # 判断是否断开连接：5s 之内接收到的全部是空字符串则认为断开连接
            if not received:
                if not received_null_time:
                    received_null_time = time.time()
                else:
                    if time.time() - received_null_time > 5:
                        print('接收失败，失败原因: 5s 内接收的全部是空字符串，可能客户端断开了连接')

                        TRANS_ERROR_LIST.append({
                            'file_name': file_name,
                            'error_msg': '5s 内接收的全部是空字符串，可能客户端断开了连接',
                        })
                        # 关闭文件、删除已接收的文件
                        f.close()
                        os.remove(os.path.join(RECEIVE_DIR, file_name))
                        break
            else:
                received_null_time = ''

        # 判断文件是否已全部接收完毕
        if received_size >= file_size:
            # 最后再设置一次进度条
            if len(received_times) == 1:
                received_times.append(time.time())

            progress_bar(file_size, received_size, '0.0M/s', fix_show_bar=True)

            server.send('5'.encode())
            return_code = int(server.recv(1024))
            if return_code == 0:
                print('\n传输失败，请重试！')
                TRANS_ERROR_LIST.append({
                    'file_name': file_name,
                    'error_msg': '未知错误，接收失败！',
                })
            else:
                end_time = time.time()
                print('\n\t用时：{0:.2f} s\n\t文件保存路径为：{1}'.format(
                    (end_time - start_time), str(save_path.absolute())
                ))

            f.close()
            break


def trans_client(host, port, file_path, use_zip):
    """
    客户端发送文件方法
    :param host: 服务端地址
    :param port: 服务端端口
    :param file_path: 传输文件路径
    :return:
    """
    client = get_socket_connection(host=host, port=port, conn_type='client')
    print('连接服务端成功，准备传输数据：')
    trans_size = float(client.recv(1024))
    time.sleep(2)
    print('\t传输前数据准备完毕，开始传输文件!')

    send_start_time = time.time()

    if use_zip:
        trans_cache = Path('trans_cache')
        if not trans_cache.exists():
            trans_cache.mkdir(parents=True)

        print('\n使用压缩传输，开始压缩文件：')
        file_path = zip_files(file_path, str(trans_cache))
        print('\n文件压缩完成，压缩后文件路径为：\n\t-- {0}\n'.format(str(file_path.absolute())))
    else:
        file_path = Path(file_path)

    files_list = get_files_list(file_path)

    current_number = 1
    for sub_file in files_list:
        sub_file_obj = Path(sub_file)

        # sub_file 为文件的绝对路径，这里需要相对于传输目录的相对路径
        sub_file_relative_path = '{0}/{1}'.format(
            file_path.name,
            sub_file.split(file_path.name)[-1]
        )

        # 传输信息
        trans_info = {
            'total_files': len(files_list),  # 总共需要传输的文件数量
            'current_number': current_number,  # 当前传递第几个文件数
            'use_zip': use_zip,  # 是否是压缩传输
            'file_info': {
                'file_name': sub_file_obj.name,
                'file_relative_path': sub_file_relative_path,
                'file_absolute_path': sub_file,
                'file_size': sub_file_obj.stat().st_size,
            }
        }

        # 向服务端传输文件信息
        client.send(json.dumps(trans_info).encode())
        send_file(client, trans_info, trans_size)

        current_number += 1

    client.close()

    # 清理压缩 cache 目录
    if use_zip:
        print('\n\n开始清理压缩文件的缓存目录：')
        trans_cache = Path('trans_cache')
        if trans_cache.exists():
            shutil.rmtree(str(trans_cache.absolute()))
        print('\t--清理 {0} \n\n压缩文件缓存目录清理完毕！\n'.format(str(trans_cache.absolute())))

    global TRANS_ERROR_LIST
    send_end_time = time.time()
    print('\n全部发送完毕，共 {0} 个文件，成功 {1} 个，失败 {2} 个， 共用时 {3:.2f} s'.format(
        len(files_list),
        len(files_list) - len(TRANS_ERROR_LIST),
        len(TRANS_ERROR_LIST),
        send_end_time - send_start_time
    ))

    if TRANS_ERROR_LIST:
        for error_file in TRANS_ERROR_LIST:
            print('\n发送失败文件名：{0}, 失败原因：{1}'.format(
                error_file['file_name'],
                error_file['error_msg']
            ))

    sys.exit()


def send_file(client, trans_info, trans_size):
    """
    发送文件方法
    :param client: 客户端连接
    :param trans_info: 传输信息
    :param trans_size: 每次传送的大小
    :return:
    """
    file_name = trans_info['file_info']['file_name']
    file_size = trans_info['file_info']['file_size']

    print_msg('send', trans_info, trans_size)

    # 每次发送的时间列表
    send_times = []
    send_size = 0

    # 服务端无响应时记录的时间
    server_timeout = ''

    f = open(trans_info['file_info']['file_absolute_path'], 'rb')

    start_time = time.time()

    global TRANS_ERROR_LIST

    # 先设置一次进度条
    progress_bar(file_size, send_size, '0.0M/s')
    while True:
        return_code = int(client.recv(1024))
        if return_code == 1:
            # 发送前记录传输时间
            send_times.append(time.time())

            # 读取文件并发送
            file_content = f.read(int(trans_size))
            if not file_content:
                progress_bar(file_size, send_size, '0.0M/s', fix_show_bar=True)
                end_time = time.time()
                print('\n传输结束，共用时：{0:.2f}s'.format(end_time-start_time))
                break

            client.sendall(file_content)

            # 记录本次发送后的信息
            send_size += trans_size

            if len(send_times) > 1:
                # 计算传输速度
                speed = get_speed(trans_size, send_times)
                # 设置进度条
                progress_bar(file_size, send_size, speed)
                # 初始化时间列表
                send_times = send_times[-1:]

            server_timeout = ''
        elif return_code == 5:
            file_content = f.read(int(trans_size))
            if file_content:
                client.send('0'.encode())
                print('\n服务端判断文件已接收完毕，但实客户端实际还没有发送完毕，传输失败')

                TRANS_ERROR_LIST.append({
                    'file_name': file_name,
                    'error_msg': '服务端判断文件已接收完毕，但实客户端实际还没有发送完毕，传输失败',
                })
            else:
                client.send('1'.encode())
                progress_bar(file_size, send_size, '0.0M/s', fix_show_bar=True)
                end_time = time.time()
                print('\n\t用时：{0:.2f}s'.format(end_time-start_time))

            break
        else:
            if not server_timeout:
                server_timeout = time.time()

            if time.time() - server_timeout > 2 * 60:
                print('\n服务端两分钟内没有返回接收信息，断开连接')
                TRANS_ERROR_LIST.append({
                    'file_name': file_name,
                    'error_msg': '服务端两分钟内没有返回接收信息，断开连接',
                })
                break
    f.close()


def main():
    """
    脚本入口
    :return:
    """
    args = set_argparse()

    # 服务端
    if args.type == 'server':
        # 没有指定每次传输的大小则设置为 1M
        trans_size = args.Mbps * (1024 ** 2) if args.Mbps else 1048576

        port = args.port if args.port else 8080

        trans_server(trans_size, port)

    # 客户端
    if args.type == 'client':
        if not args.address:
            print('客户端必须要指定服务端的地址')
            sys.exit()

        if not args.path:
            print('客户端必须要指定传输文件地址')
            sys.exit()
        else:
            file_path = args.path
            if not os.path.exists(file_path):
                print('传输文件不存在，请检查文件路径是否输入正确。本次输入的文件路径：{0}'.format(file_path))
                sys.exit()
            else:
                file_path = os.path.abspath(file_path)

        port = args.port if args.port else 8080
        use_zip = True if args.zip else False

        trans_client(args.address, port, file_path, use_zip)


if __name__ == '__main__':
    main()
