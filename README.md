# LAN-file-transfer
局域网传输文件Python脚本：

1、使用方法：(在命令行里运行)
	服务端：接收文件，在命令行里输入
		trans.py [参数1]
		（参数1：每次传输的大小，可选，默认最大为2048000 b，
				0、1、2、3分别代表的大小为：
					0: 10240 b
					1: 102400 b
					2: 512000 b
					3: 1024000 b
				可根据路由器的配置在 “def recv_data(num=2048000):”处修改合适的大小）
	客户端：传输文件，在命令行里输入
		trans.py [参数1] [参数2]
		（参数1：要传输的文件名   参数2：服务器IP）
		
	注：1、接收文件的位置就在打开命令行的位置，所以请先到要接收的文件夹后打开命令行，
	      或者打开命令行后cd到要接收的位置再执行本脚本
	   2、传输文件可以在任何地方，只要参数2写为要传输文件的绝对路径 
		 如：/home/azazel/test/test.txt
2、Linux或Windows下配置全局运行方法：
	（1）linux
		A: 将脚本的第一行代码改为(python2安装位置)
			#!/usr/bin/python
		B: 为文件添加可执行权限
			chmod 755 trans.py 或 chmod +x trans.py  (具体方法百度)
		C：创建一个文件夹，设置为全局运行，然后将trans.py放入，就可以在任何地方运行（详细设置过程参考我的gitbub中note仓库里的Ubuntu环境变量设置文档）
	（2）Windows
		A: 将脚本的第一行代码改为(python2安装位置，实际情况根据自己的安装位置)
			#!C:\Program Design\Python\python2\python.exe
		B：在C盘下创建文件夹后将其加入环境变量path,然后将trans.py放入，就可以在任何地方运行
		C: 设置trans.py的默认执行程序为python.exe
注：
    本脚本在Linux下可以去掉.py后缀，直接执行trans
    本脚本使用的前提是要能ping通两台机器的网络
    本脚本写的初衷是方便在linux下传输文件，在windows下可能存在着一系列未知的BUG
    本脚本只是作者在学习Python初期练习的一个小程序，代码有不合理的地方望各位大神一笑了之
    本脚本只适用于python爱好者交流学习
