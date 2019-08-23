import socket
import simplejson


def send(_ip, _port, _id, _method, _params):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((_ip, _port))
    send_data = {'id': _id, 'method': _method, 'params': _params}
    s.send(b"%s\n" % simplejson.dumps(send_data).encode())
    data = s.recv(1024).decode()
    s.close()
    return data
