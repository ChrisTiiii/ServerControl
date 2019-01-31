'''
TCP Server Version 1.0
2018.12.12
York
    js = json.dumps({
        "From": "Server",   # send information terminal
        "SendTo": contact,  # recive information terminal
        "Time": ctime()     # sending time
        "Type": "command",    # information type
        "Status": "success" # reply status
        "Command": "command" # command
        "Msg": server_msg,  # message
        })
'''
import selectors
import threading
import queue
# import re
import socket
from time import ctime, time
import json

hostname = socket.gethostname()  # 获取本地主机名
sysinfo = socket.gethostbyname_ex(hostname)
hostip = sysinfo[2][0]
HOST = hostip

BUFSIZE = 1024
PORT = 2222
ADDR = (HOST, PORT)
tcpServSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcpServSock.bind(ADDR)
tcpServSock.listen(20)

user_list = []  # all registered users
user_buff = {}  # each user has a buffer
acti_user = []  # once a user logs in, he/she becomes active
acti_user_list = []

sel = selectors.DefaultSelector()
lock = threading.Lock()


#  client connect to server  and login
def recv():
    global tcpServSock
    while True:
        lock.acquire(blocking=True)
        ret = sel.select(timeout=1)
        lock.release()
        for key, event in ret:  # some socket is readable
            if key.fileobj == tcpServSock:  # a new connection comes
                new_socket, new_addr = tcpServSock.accept()
                print('connected from %s [%s]' % (new_addr, ctime()))  # add to log
                lock.acquire(blocking=True)
                sel.register(new_socket, selectors.EVENT_READ)
                lock.release()
            else:  # some one clicked Log In
                try:
                    msg = key.fileobj.recv(BUFSIZE).decode('utf-8')
                    msg = msg.split('\0')
                    js = json.loads(msg[0])
                    ID = js["From"]
                except:
                    print('%s disconnected' % (key.fileobj))  # add to log
                    lock.acquire(blocking=True)
                    sel.unregister(key.fileobj)
                    lock.release()
                    continue
                if ID not in user_list:
                    server_msg = 'FROME SERVER: no such user for logged in (1)'
                    js = json.dumps({
                        "From": "Server",
                        "SendTo": ID,
                        "Time": ctime(),
                        "Type": "Reply",
                        "Status": "error1",
                        "Command": "none",
                        "Msg": server_msg
                    })
                    key.fileobj.send(bytes(js + '\r', 'utf-8'))
                    print('%s no such user [%s]' % (ID, ctime()))
                    continue
                else:
                    if ID in acti_user_list:  # already logged in, deny
                        server_msg = 'FROME SERVER: already logged in (2)'
                        js = json.dumps({
                            "From": "Server",
                            "SendTo": ID,
                            "Time": ctime(),
                            "Type": "Reply",
                            "Status": "error2",
                            "Command": "none",
                            "Msg": server_msg
                        })
                        key.fileobj.send(bytes(js + '\r', 'utf-8'))
                        continue
                    else:
                        acti_user_list.append(ID)
                    print('%s logged in [%s]' % (ID, ctime()))
                user = User(key.fileobj, ID)  # create an instance for logged in user
                acti_user.append(user)
                user()
                lock.acquire(blocking=True)
                sel.unregister(key.fileobj)
                lock.release()


# server forward client's message to another
def forward():
    while True:
        for eachUser in acti_user:
            if eachUser.zombie == True:  # this user has logged out
                lock.acquire(blocking=True)
                sel.register(eachUser.socket, selectors.EVENT_READ)  # after user's loging out,
                # recv_thread will take over the socket and listen to it
                lock.release()
                acti_user.remove(eachUser)
                del (eachUser)
                continue
            if eachUser.death == True:
                acti_user.remove(eachUser)
                del (eachUser)
                continue
            while user_buff[eachUser.ID].qsize():
                msg = user_buff[eachUser.ID].get()
                # some ckecking is desired, for the socket may not be writable
                eachUser.socket.send(bytes(msg + '\r', 'utf-8'))


# client connect to another
class User(object):
    def __init__(self, socket, ID):
        self.socket = socket
        self.ID = ID
        self.zombie = False
        self.death = False
        self.contact = None
        self.sel = selectors.DefaultSelector()
        self.sel.register(self.socket, selectors.EVENT_READ)

    def recv(self):
        while True:
            self.sel.select()
            try:
                data = self.socket.recv(BUFSIZE).decode('utf-8')
                data = data.split('\0')
                js = json.loads(data[0])
                user = js["From"]
                msgtype = js["Type"]
                sendto = js["SendTo"]
                msg = js["Msg"]
                datatype = js["Type"]
                if (sendto == 'All'):
                    self.contact = sendto
            except:
                print('%s disconnected' % (self.ID))
                acti_user_list.remove(self.ID)
                self.death = True
                return None
            if datatype == 'Command':
                JsonStr = json.dumps(js)
                arr = json.loads(JsonStr)
                command = arr["Command"]
            else:
                command = 'none'
            if msgtype == 'Connect':
                # user wants to contact with some one
                contact = sendto
                if contact not in user_list:
                    server_msg = 'FROME SERVER: no such user (3)'
                    js = json.dumps({
                        "From": "Server",
                        "SendTo": contact,
                        "Time": ctime(),
                        "Type": datatype,
                        "Status": "error3",
                        "Command": "none",
                        "Msg": server_msg
                    })
                    self.socket.send(bytes(js + '\r', 'utf-8'))
                else:
                    if contact not in acti_user_list:
                        server_msg = 'FROME SERVER: this user is not active (4)'
                        js = json.dumps({
                            "From": "Server",
                            "SendTo": contact,
                            "Time": ctime(),
                            "Type": datatype,
                            "Status": "error4",
                            "Command": "none",
                            "Msg": server_msg
                        })
                        self.socket.send(bytes(js + '\r', 'utf-8'))
                    else:
                        server_msg = 'FROME SERVER: this user is active'
                        js = json.dumps({
                            "From": "Server",
                            "SendTo": contact,
                            "Time": ctime(),
                            "Type": datatype,
                            "Status": "Success",
                            "Command": "none",
                            "Msg": server_msg
                        })
                        self.socket.send(bytes(js + '\r', 'utf-8'))
                    self.contact = sendto
            elif msgtype == 'Logout':
                # user wants to log out
                acti_user_list.remove(self.ID)
                print('%s logged out [%s]' % (self.ID, ctime()))
                self.zombie = True
                print(self.zombie)
                return None
            elif msgtype == 'GetId':
                contact = sendto
                getuser_list = list(user_list)
                for item in getuser_list[:]:  # getuser_list[:]对原list拷贝从而获取新的序号
                    if len(item) != 6:
                        getuser_list.remove(item)
                js = json.dumps({
                    "From": "Server",
                    "SendTo": "client",
                    "Time": ctime(),
                    "Type": "userlist",
                    "Status": "success",
                    "Command": "none",
                    "Msg": getuser_list
                })
                self.socket.send(bytes(js + '\r', 'utf-8'))

            elif self.contact != None:
                if self.contact == 'All':
                    js = json.dumps({
                        "From": self.ID,
                        "SendTo": contact,
                        "Time": ctime(),
                        "Type": datatype,
                        "Status": "success",
                        "Command": command,
                        "Msg": msg
                    })
                    for i, val in enumerate(acti_user_list):
                        user_buff[val].put(js + '\r')
                        i += 1
                elif contact in acti_user_list:
                    js = json.dumps({
                        "From": self.ID,
                        "SendTo": contact,
                        "Time": ctime(),
                        "Type": datatype,
                        "Status": "success",
                        "Command": command,
                        "Msg": msg
                    })
                    user_buff[self.contact].put(js + '\r')
                else:
                    server_msg = 'FROME SERVER: choose a contact first (5)'
                    js = json.dumps({
                        "From": "Server",
                        "SendTo": contact,
                        "Time": ctime(),
                        "Type": "Reply",
                        "Status": "error5",
                        "Command": "none",
                        "Msg": server_msg
                    })
                    self.socket.send(bytes(js + '\r', 'utf-8'))

    def __call__(self):
        self.recv_thread = threading.Thread(target=self.recv)
        self.recv_thread.daemon = True
        self.recv_thread.start()


def socketstart():
    fd = open(r'.\user.ini', 'r+')  # read txt userdata
    for eachUser in fd:
        user_list.append(eachUser.strip())
        user_buff[eachUser.strip()] = queue.Queue(4096)
    print(user_list)

    sel.register(tcpServSock, selectors.EVENT_READ)

    recv_thread = threading.Thread(target=recv)
    recv_thread.daemon = True
    recv_thread.start()

    forward_thread = threading.Thread(target=forward)
    forward_thread.daemon = True
    forward_thread.start()
    print('server ' + hostip + ' start success at port ' + str(PORT))  # add to log

    while True:
        pass  # infinate loop


if __name__ == '__main__':
    socketstart()
