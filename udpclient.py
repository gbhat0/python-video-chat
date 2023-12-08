import socket
import cv2
import math
import struct
import numpy as np

max_size = 2**16
max_image_dgram = max_size - 64

class UDPClient(object):
    def __init__(self, role, server_addr):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.settimeout(10)    
        self.role = role
        self.server_addr = server_addr
    
    def send_identification(self):
        self.client_socket.sendto(self.role.encode(), self.server_addr)

    def wait_for_receiver(self):
        data, addr = self.client_socket.recvfrom(max_size)
        print("wait_for_receiver", data)
        if data.decode() == "receiver_connected":
            self.handle_camera()

    def handle_camera(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Camera Not Found....")
            return

        while cap.isOpened():
            ret, frame = cap.read()
            self.send_to_server(frame)

        cap.release()
        cv2.destroyAllWindows()


    def send_to_server(self, frame):
        compress_frame = cv2.imencode('.jpg', frame)[1]
        dat = compress_frame.tostring()
        size = len(dat)
        num_of_segments = math.ceil(size/(max_image_dgram))
        array_pos_start = 0
    
        while num_of_segments:
            array_pos_end = min(size, array_pos_start + max_image_dgram)
            print(array_pos_end)
            self.client_socket.sendto(
                   struct.pack('B', num_of_segments) +
                   dat[array_pos_start:array_pos_end],
                   self.server_addr
                   )
            array_pos_start = array_pos_end
            num_of_segments -= 1
    
    def wait_for_sender(self):
        data, addr = self.client_socket.recvfrom(max_size)
        print("wait_for_sender", data)
        if data.decode() == "sender_ready":
            self.receive_from_server()
        else:
            print("sender not ready")

    def receive_from_server(self):
        dat = b''
        while True:
            print("receiving")
            seg, addr = self.client_socket.recvfrom(max_size)
            if struct.unpack('B', seg[0:1])[0] > 1:
                dat += seg[1:]
            else:
                dat += seg[1:]
                img = cv2.imdecode(np.fromstring(dat, dtype=np.uint8), 1)
                cv2.imshow('frame', img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                dat = b''
        # cap.release()
        cv2.destroyAllWindows()
        self.client_socket.close()