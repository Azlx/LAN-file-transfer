# 传输文件脚本（python3）

## 脚本说明
1. 此脚本分为服务端和客户端
2. 服务端为文件的接收者
3. 客户端为文件的发送者

## 使用方法
先启动服务端：`python trans.py server {optional}` (可选则使用"-p"和"-m"参数)

再启动客户端：`python trans.py client {optional}` (必须指定"-a","-P"参数,可选择使用"-p"参数)

各参数说明：
> positional arguments:
>>{server,client}       server or client
>
> optional arguments:
>> -h, --help            show this help message and exit
>>
>> -a ADDRESS, --address ADDRESS 连接地址
>> 
>> -p PORT, --port PORT  端口, default=8080
>> 
>> -P PATH, --path PATH  传输文件路径
>>
>> -m MBPS, --Mbps MBPS  每次传输的数据包大小, default=1Mbps. 注意：此选项的大小取决于网络带宽，设置过大可能会导致传输失败
 
