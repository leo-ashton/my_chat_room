import socket
import threading
import json
import zlib
import traceback


class Message:
    def __init__(self, text=None, message_type='broadcast', sender_id=1, sender_nickname='User', receiver_id=None, message_No=0, burn=0, filename=None):
        self.text = text
        self.message_type = message_type
        self.sender_id = sender_id
        self.sender_nickname = sender_nickname
        self.receiver_id = receiver_id
        self.message_No = message_No
        self.burn = burn
        self.filename = filename
        if text != None:
            self.CRC32 = zlib.crc32(self.text.encode())
        else:
            self.CRC32 = 0

    def byte(self):
        ret = json.dumps({
            'text': self.text,
            'message_type': self.message_type,
            'sender_id': self.sender_id,
            'sender_nickname': self.sender_nickname,
            'receiver_id': self.receiver_id,
            'CRC32': self.CRC32,
            'message_No': self.message_No,
            'burn': self.burn,
            'filename': self.filename
        }).encode()
        return ret


class Server:
    """
    服务器类
    """

    def __init__(self):
        """
        构造
        """
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__connections = list()
        self.__nicknames = list()

    def __user_thread(self, user_id):
        """
        用户子线程
        :param user_id: 用户id
        """
        connection = self.__connections[user_id]
        nickname = self.__nicknames[user_id]
        print('[Server] 用户', user_id, nickname, '加入聊天室')
        self.__broadcast(Message(text='用户 ' + str(nickname) +
                         '(' + str(user_id) + ')' + '加入聊天室'))

        # 侦听
        while True:
            # noinspection PyBroadException
            try:
                buffer = connection.recv(1024).decode()
                # 解析成json数据
                obj = json.loads(buffer)
                if obj['CRC32'] != zlib.crc32(obj['text'].encode()):
                    print("[Server] 收到损坏的报文")

                # 如果是广播指令
                if obj['message_type'] == 'broadcast':
                    self.__broadcast(message=Message(text=obj['text'], message_type=obj['message_type'],
                                     sender_id=obj['sender_id'], sender_nickname=self.__nicknames[int(obj['sender_id'])]))
                    print(f"向{obj['sender_id']}发送报文")
                   # self.__broadcast(
                   #     user_id=obj['sender_id'], text=obj['text'])

                elif obj['message_type'] == 'unicast' or obj['message_type'] == 'file':
                    self.__unicast(
                        receiver_id=obj['receiver_id'], message=Message(text=obj['text'], message_type=obj['message_type'],
                                                                        sender_id=obj['sender_id'],
                                                                        sender_nickname=self.__nicknames[int(obj['sender_id'])], filename=obj['filename']))

                elif obj['message_type'] == 'logout':
                    print('[Server] 用户', user_id, nickname, '退出聊天室')
                    self.__broadcast(Message(
                        text='用户 ' + str(nickname) + '(' + str(user_id) + ')' + '退出聊天室'))
                    self.__connections[user_id].close()
                    self.__connections[user_id] = None
                    self.__nicknames[user_id] = None
                    break

                else:
                    print('[Server] 无法解析json数据包:',
                          connection.getsockname(), connection.fileno())
            except Exception:
                print('[Server] 连接失效:', connection.getsockname(),
                      connection.fileno())
                traceback.print_exc()
                self.__connections[user_id].close()
                print("已关闭连接")
                self.__connections[user_id] = None
                self.__nicknames[user_id] = None

    def __broadcast(self, message, transit_data=None, user_id=None):
        """
        广播
        :param user_id: 用户id(0为系统)
        :param message: Message 类对象
        :param transit_data: byte 对象
        """

        if transit_data != None:
            if user_id != i and self.__connections[i]:
                # user_id != i 是因为不需要将广播信息传回给发送者
                self.__connections[i].send(transit_data)

        if message.message_type == 'broadcast':
            for i in range(1, len(self.__connections)):
                if message.receiver_id != i and self.__connections[i]:
                    self.__connections[i].send(message.byte())
        else:
            print("[Server] 非广播数据报被传入broadcast函数!")

    def __unicast(self, receiver_id, message):
        receiver_id = int(receiver_id)
        if receiver_id > 0 and receiver_id < len(self.__connections):
            self.__connections[receiver_id].send(message.byte())
        else:
            print("[Server] 私信了不存在的用户")

    def __waitForLogin(self, connection):
        # 尝试接受数据
        # noinspection PyBroadException
        try:
            buffer = connection.recv(1024).decode()
            # 解析成json数据
            obj = json.loads(buffer)
            # 如果是连接指令，那么则返回一个新的用户编号，接收用户连接
            if obj['message_type'] == 'login':
                self.__connections.append(connection)
                self.__nicknames.append(obj['nickname'])
                connection.send(json.dumps({
                    'id': len(self.__connections) - 1
                }).encode())

                # 开辟一个新的线程
                thread = threading.Thread(
                    target=self.__user_thread, args=(len(self.__connections) - 1,))
                thread.setDaemon(True)
                thread.start()
            else:
                print('[Server] 无法解析json数据包:',
                      connection.getsockname(), connection.fileno())
        except Exception:
            print('[Server] 无法接受数据:', connection.getsockname(),
                  connection.fileno())

    def start(self):
        """
        启动服务器
        """
        # 绑定端口
        self.__socket.bind(('127.0.0.1', 52000))
        # 启用监听
        self.__socket.listen(10)
        print('[Server] 服务器正在运行......')

        # 清空连接
        self.__connections.clear()
        self.__nicknames.clear()
        self.__connections.append(None)
        self.__nicknames.append('System')

        # 开始侦听
        while True:
            connection, address = self.__socket.accept()
            print('[Server] 收到一个新连接', connection.getsockname(),
                  connection.fileno())

            thread = threading.Thread(
                target=self.__waitForLogin, args=(connection,))
            thread.setDaemon(True)
            thread.start()
