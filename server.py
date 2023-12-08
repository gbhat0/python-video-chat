import asyncio
import struct
import enum
import math

CLIENTS = {}
MAX_DGRAM = 2**16
MAX_IMAGE_DGRAM = MAX_DGRAM - 64

HOME_APP_PAIRS = {'192.168.29.126':['192.168.29.126', '192.168.29.103'],
                  }
CONNECTED_SENDERS = {}

class STATES(enum.Enum):
    NEW = 0
    IDENTIFY = 1
    SENDER_WAIT = 2
    SENDER_READY = 3
    RECEIVER_READY = 4

class MyClient:
    def __init__(self, transport, addr):
        self.addr = addr
        self.transport = transport
        self.id = addr[0] + str(addr[1])
        self.state = STATES.NEW
        self.clearbuf()
        self.framequeue = asyncio.Queue()
        self.show_frame_coro = asyncio.create_task(self.processframe())
    
    def process_packet(self, data):
        if self.state == STATES.NEW:
            self.identify(data)
        elif self.state == STATES.SENDER_READY:
            self.process_video_data(data)

    def identify(self, data):
        role = data.decode()
        print("identify", role)
        if role == "sender":
            if self.addr[0] in HOME_APP_PAIRS:
                self.state = STATES.SENDER_WAIT
                print("identify", "adding to senders")
                CONNECTED_SENDERS[self.addr[0]] = self
        elif role == "receiver":
            for s, r in HOME_APP_PAIRS.items():
                if self.addr[0] in r:
                    if s in CONNECTED_SENDERS:
                        CONNECTED_SENDERS[s].update_receiver(self)
                        self.state = STATES.RECEIVER_READY
                        self.transport.sendto(b"sender_ready", self.addr)
                    else:
                        self.transport.sendto(b"sender_unavailable", self.addr)

    async def processframe(self):
        while True:
            frame =  await self.framequeue.get()
            #print("popped frame", self.id, len(frame))
            '''
            img = cv2.imdecode(np.fromstring(frame, dtype=np.uint8), 1)
            cv2.imshow(str(self.id), img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            '''
            #self.receiver.send_frame(frame)
            [r.send_frame(frame) for r in self.receivers]

    def clearbuf(self):
        self.buff = b''
    
    def appendbuf(self, dat):
        #print("appending buffer:", self.addr, len(dat))
        self.buff += dat
    
    def put_in_frame_queue(self):
        #print("Putting in queue:", self.addr, len(self.buff))
        self.framequeue.put_nowait(self.buff)
        self.clearbuf()

    def process_video_data(self, data):
        if struct.unpack("B", data[0:1])[0] > 1:
            self.appendbuf(data[1:])
        else:
            self.appendbuf(data[1:])
            self.put_in_frame_queue()
    
    def update_receiver(self, receiver):
        if not getattr(self,'receivers', None):
            self.receivers = []
        self.receivers.append(receiver)
        self.state = STATES.SENDER_READY
        self.transport.sendto(b"receiver_connected", self.addr)   
    
    def send_frame(self, frame):
        #print("sending video to receiver", self.addr, self.transport)
        size = len(frame)
        num_of_segments = math.ceil(size/(MAX_IMAGE_DGRAM))
        array_pos_start = 0
    
        while num_of_segments:
            array_pos_end = min(size, array_pos_start + MAX_IMAGE_DGRAM)
            print(array_pos_end)
            self.transport.sendto(
                   struct.pack('B', num_of_segments) +
                   frame[array_pos_start:array_pos_end],
                   self.addr
                   )
            array_pos_start = array_pos_end
            num_of_segments -= 1

class UDPServer(object):
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        client_endpoint = addr[0] +":" + str(addr[1])
        if client_endpoint not in CLIENTS:
            CLIENTS[client_endpoint] = MyClient(self.transport, addr)
            print("New client:", addr, len(CLIENTS))
        CLIENTS[client_endpoint].process_packet(data)
    
async def main():
    print("Server Listening.....")
    print(HOME_APP_PAIRS)
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPServer(),
        local_addr=('0.0.0.0', 9999),
        )
    try:
        await asyncio.sleep(3600)  # Serve for 1 hour.
    finally:
        transport.close()

if __name__ == "__main__":
    asyncio.run(main())