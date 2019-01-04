import io
import os
import socket
import struct
import time
import datetime
from PIL import Image

def recv_msg(sock):
    # Read message length and unpack it into an longint
    raw_msglen = recvall(sock,struct.calcsize('<L'))
    if not raw_msglen:
        return None
    msglen = struct.unpack('<L', raw_msglen)[0]
    # Read the message data
    return recvall(sock, msglen)

def recvall(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

# Start a socket listening for connections on 0.0.0.0:8000 (0.0.0.0 means
# all interfaces)
server_socket = socket.socket()
server_socket.bind(('0.0.0.0', 8000))
server_socket.listen(1)

conn, addr = server_socket.accept()
counter = 1

#target_dir = '/home/iplab/Projects/PBLDrone/detected'
target_dir = '/home/pi/Desktop/detected'    
try:
    while True:
    
        # Read the message data
        data = recv_msg(conn)
        
        if not os.path.exists(target_dir):
                os.mkdir(target_dir)
                
        timestamp = datetime.datetime.now()
        ts = timestamp.strftime("%d-%m-%y-%I%M%S%p")

        target ='{}/frame_{}_{timestamp}.jpg'.format(target_dir,counter,timestamp=ts)
        
        if data is not None:
            myfile = open(target, 'wb')
            if not data:
                myfile.close()
                break
            myfile.write(data)
            myfile.close()

            print('Detected Frame {} Received'.format(counter))
            counter+=1
        else:
            break
finally:
    conn.close()
    server_socket.close()
