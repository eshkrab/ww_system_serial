import json
import logging
import serial
import asyncio
import time
import zmq
import zmq.asyncio

class Player:
    def __init__(self, brightness=250.0, fps=30, state="stopped", mode="repeat", current_media=None):
        self.state = state
        self.mode = mode
        self.brightness = brightness
        self.fps = fps
        self.current_media = current_media


############################
# CONFIG
############################
def load_config(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config

def get_log_level( level):
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return levels.get(level.upper(), logging.INFO)

config = load_config('config/config.json')

logging.basicConfig(level=get_log_level(config['debug']['log_level']))

############################
# PLAYER
############################
player = Player(brightness=config['brightness_level'], fps=config['fps'])

########################
# SERIAL
########################
serial_port = config['serial']['port']
serial_baudrate = config['serial']['baudrate']
ser = serial.Serial(serial_port, serial_baudrate)

########################
# ZMQ
########################
ctx = zmq.asyncio.Context()
# Publish to the player app
pub_socket = ctx.socket(zmq.PUB)
pub_socket.bind(f"tcp://{config['zmq']['ip_bind']}:{config['zmq']['port_serial_pub']}")  # Publish to the player app

# Subscribe to the player app
sub_socket = ctx.socket(zmq.SUB)
sub_socket.connect(f"tcp://{config['zmq']['ip_connect']}:{config['zmq']['port_player_pub']}")  
sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

logging.debug(f"Subscribing to tcp://{config['zmq']['ip_connect']}:{config['zmq']['port_player_pub']}")

def reset_socket():
    global sub_socket
    logging.debug("Resetting socket")
    # close the current socket
    sub_socket.close()
    # create a new socket
    new_sock = ctx.socket(zmq.SUB)
    logging.debug(f"Subscribing to tcp://{config['zmq']['ip_connect']}:{config['zmq']['port_player_pub']}")

    # connect the new socket
    try:
        logging.debug(f"OPENING UP SOCKET AGAIN to tcp://{config['zmq']['ip_connect']}:{config['zmq']['port_player_pub']}")
        new_sock.connect(f"tcp://{config['zmq']['ip_connect']}:{config['zmq']['port_player_pub']}")  
        new_sock.setsockopt_string(zmq.SUBSCRIBE, "")
    except zmq.ZMQError as zmq_error:
        logging.error(f"Subscribing to tcp://{config['zmq']['ip_connect']}:{config['zmq']['port_player_pub']}")
        logging.error(f"ZMQ Error occurred during socket reset: {str(zmq_error)}")
    return new_sock

LAST_MSG_TIME = time.time()

async def monitor_socket():
    #monitor sub_socket and if it's been too long since LAST_MSG_TIME, reset the socket
    global sub_socket
    global LAST_MSG_TIME
    logging.debug("Monitoring socket")
    while True:

        #  logging.debug(f"Time since last message: {time.time() - LAST_MSG_TIME}")
        # Check if it's been 1 minute since last message received
        if time.time() - LAST_MSG_TIME > 10:
            logging.debug("Resetting socket")
            fut = asyncio.ensure_future(sub_socket.recv())
            try:
                resp = await asyncio.wait_for(fut, timeout=0.5)  # Close the previous socket only after a short time-out
                LAST_MSG_TIME = time.time()
                logging.debug("New message received, not resetting the socket!")
            except asyncio.TimeoutError:
                sub_socket = reset_socket(sub_socket)
                LAST_MSG_TIME = time.time()

        await asyncio.sleep(1)

async def send_message_to_player(message):
    try:
        logging.debug(f"Publishing message: {message}")
        await pub_socket.send_string(message)
    except zmq.ZMQError as e:
        logging.error(f"ZMQError while publishing message: {e}")
        return -1


async def subscribe_to_player():
    global sub_socket
    global LAST_MSG_TIME

    logging.debug("SUBSCRIBED to player")

    while True:
        #  logging.debug("Waiting for message from player")
        message = await sub_socket.recv_string()
        LAST_MSG_TIME = time.time()
        #  logging.debug(f"Received from Player: {message}")


        # Process the received message
        message = message.split(" ")
        if message[0] == "state":
            player.state = message[1]
        elif message[0] == "mode":
            player.mode = message[1]
        elif message[0] == "brightness":
            brightness = float(message[1]) / 255.0
            player.brightness = float(brightness)
        elif message[0] == "fps":
            player.fps = int(message[1])
        elif message[0] == "current_media":
            player.current_media = message[1]
        else:
            logging.error(f"Unknown message from Player: {message}")

        await asyncio.sleep(0.1)


async def handle_zmq_to_serial():
    while True:
        print("handle_zmq_to_serial")
        #  #  message = await socket.recv_string()
        #  message = "serial test"
        #  #  logging.debug(f"Received message from ZeroMQ: {message}")
        #
        #  # Write the message to the serial port
        #  ser.write(message.encode())
        await asyncio.sleep(0.1)

async def handle_serial_to_zmq():
    while True:
        logging.debug("handle_serial_to_zmq")
        if ser.in_waiting:
            data = ser.readline().decode().strip()
            logging.debug(f"Received data from Serial: {data}")
        #
        #      # Process the data or send it to ZeroMQ
        #      # Example: Send the data as a message to ZeroMQ
        #      #  await send_message_to_player(f"process_data {data}")
        #      #  logging.debug(f"Reply from player: {reply}")
        await asyncio.sleep(0.1)

async def main():
    logging.debug("Starting main")
    # Start listening to messages from player app
    await asyncio.create_task(subscribe_to_player())
    await asyncio.create_task(monitor_socket())

    logging.debug("ZMQ TASKS created")
    # Start the ZeroMQ-to-Serial and Serial-to-ZeroMQ handlers
    tasks = [
        asyncio.create_task(handle_zmq_to_serial()),
        asyncio.create_task(handle_serial_to_zmq())
    ]
    logging.debug("Tasks created")
    await asyncio.gather(*tasks)

# Start the event loop
if __name__ == '__main__':
    asyncio.run(main())

# Close Serial Port
ser.close()
