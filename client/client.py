import socket
import threading
import json
from cmd import Cmd
import zlib
import struct
import colorama
from colorama import Fore
import traceback
import time

# print(Fore.RED + 'This text is red in color')


class Message:
    def __init__(self, text=None, message_type='broadcast', sender_id=None, receiver_id=None, message_No=0):
        self.text = text
        self.message_type = message_type
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        if text != None:
            self.CRC32 = zlib.crc32(self.text.encode())
        else:
            self.CRC32 = 0
        self.message_No = message_No

    def byte(self):
        ret = json.dump({
            'text': self.text,
            'message_type': self.message_type,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'CRC32': self.CRC32,
            'message_No': self.message_No
        }).encode()
        return ret


class Client(Cmd):
    """
    客户端
    """
    prompt = ''
    intro = '[Welcome] 简易聊天室客户端(Cli版)\n' + '[Welcome] 输入help来获取帮助\n'

    def __init__(self):
        """
        构造
        """
        super().__init__()
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__id = None
        self.__nickname = None
        self.__isLogin = False

    def __receive_message_thread(self):
        """
        接受消息线程
        """
        while self.__isLogin:
            # noinspection PyBroadException
            try:
                buffer = self.__socket.recv(1024).decode()
                if buffer == '':
                    continue
                obj = json.loads(buffer)

                if obj['text'] != '' and obj['CRC32'] != zlib.crc32(obj['text'].encode()):
                    # 若无正文,则不进行校验
                    print("[Client] 收到损坏的报文")
                    continue
                if obj['message_type'] == 'broadcast':
                    print(Fore.YELLOW+'[' + str(obj['sender_nickname']) +
                          '(' + str(obj['sender_id']) + ')' + ']', obj['text'])

                elif obj['message_type'] == 'unicast':
                    print(Fore.BLUE+'[' + str(obj['sender_nickname']) +
                          '(' + str(obj['sender_id']) + ')' + ']', obj['text'])
            except Exception:
                print('[Client] 无法从服务器获取数据')
                traceback.print_exc()
                time.sleep(2)

    def __send_message_thread(self, message):
        """
        发送消息线程
        :param message: 消息内容
        """
        self.__socket.send(message)

    def start(self):
        """
        启动客户端
        """
        default_address = '127.0.0.1'
        default_port = 52000
        self.__socket.connect(('127.0.0.1', 52000))
        self.cmdloop()

    def do_login(self, args):
        """
        登录聊天室
        :param args: 参数
        """
        nickname = args.split(' ')[0]

        # 将昵称发送给服务器,获取用户id
        self.__socket.send(json.dumps({
            'message_type': 'login',
            'nickname': nickname
        }).encode())
        # 尝试接受数据
        # noinspection PyBroadException
        try:
            buffer = self.__socket.recv(1024).decode()
            obj = json.loads(buffer)
            if obj['id']:
                self.__nickname = nickname
                self.__id = obj['id']
                self.__isLogin = True
                print('[Client] 成功登录到聊天室')

                # 开启子线程用于接受数据
                thread = threading.Thread(target=self.__receive_message_thread)
                thread.setDaemon(True)
                thread.start()
            else:
                print('[Client] 无法登录到聊天室')
        except Exception:
            print('[Client] 无法从服务器获取数据')

    def do_send(self, args):
        """
        发送消息
        :param args: 参数
        """
        burn = 0

        message_type = args.split(' ')[0]
        if message_type == 'broadcast':
            receiver_id = -1
            # 此时命令形如 send broadcast hello world!
            text = ' '.join(args.split(' ')[1:])
        elif message_type == 'unicast':
            # 此时命令形如 send unicast 1 hello world!
            receiver_id = args.split(' ')[1]

            if args.split(' ')[2] == "burn":
                # 阅后即焚
                # 此时命令形如 send unicast 1 burn hello world!
                burn = 1
                text = ' '.join(args.split(' ')[3:])
            else:
                burn = 0
                text = ' '.join(args.split(' ')[2:])
        # 显示自己发送的消息
        print('[' + str(self.__nickname) +
              '(' + str(self.__id) + ')' + ']', text)
        # 开启子线程用于发送数据
        """
        json.dumps({
            'type': str(message_type),
            'sender_id': self.__id,
            'message': message,
            'CRC32': zlib.crc32(message.encode())
        }).encode()
        """
        message = json.dumps({
            'message_type': str(message_type),
            'sender_id': self.__id,
            'sender_nickname': self.__nickname,
            'receiver_id': receiver_id,
            'text': text,
            'CRC32': zlib.crc32(text.encode()),
            'burn': burn
        }).encode()
        thread = threading.Thread(
            target=self.__send_message_thread, args=(message,))
        thread.setDaemon(True)
        thread.start()

    def do_logout(self, args=None):
        """
        登出
        :param args: 参数
        """
        self.__socket.send(json.dumps({
            'message_type': 'logout',
            'sender_id': self.__id
        }).encode())
        self.__isLogin = False
        return True

    def do_help(self, arg):
        """
        帮助
        :param arg: 参数
        """
        command = arg.split(' ')[0]
        if command == '':
            print('[Help] login nickname - 登录到聊天室, nickname是你选择的昵称')
            print('[Help] send all message - 发送广播消息, message是你输入的消息')
            print(
                '[Help] send nickname message - 发送广播消息, nickname是接收者的昵称,message是你输入的消息')
            print('[Help] logout - 退出聊天室')
        elif command == 'login':
            print('[Help] login nickname - 登录到聊天室, nickname是你选择的昵称')
        elif command == 'send':
            print('[Help] send message - 发送消息, message是你输入的消息')
        elif command == 'logout':
            print('[Help] logout - 退出聊天室')
        else:
            print('[Help] 没有查询到你想要了解的指令')
