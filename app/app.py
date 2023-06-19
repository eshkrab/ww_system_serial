import zmq

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5555")
socket.setsockopt_string(zmq.SUBSCRIBE, "")

print("I am ready to receive")

topic = b'brightness\0'
message = "100"

while True:
    print(socket.recv_string())

