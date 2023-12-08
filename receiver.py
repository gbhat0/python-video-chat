from udpclient import UDPClient

if __name__ == "__main__":
    obj = UDPClient("receiver",("192.168.29.126", 9999))
    obj.send_identification()
    obj.wait_for_sender()
