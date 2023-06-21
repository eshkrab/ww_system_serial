import json
import logging
import serial
import asyncio
import time
import zmq
import zmq.asyncio
#  from modules.zmqcomm import subscribe_to_messages


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

async def subscribe_to_messages( ip_connect, port, process_message):
    logging.info("Started listening to messages")

    ctx = zmq.asyncio.Context.instance()
    sub_sock = ctx.socket(zmq.SUB)
    sub_sock.connect(f"tcp://{ip_connect}:{port}")
    sub_sock.setsockopt_string(zmq.SUBSCRIBE, "")
    logging.debug("socket port: "+ str(sub_sock.getsockopt(zmq.LAST_ENDPOINT)))

    try:
        while True:
            message = await sub_sock.recv_string()
            process_message(message)
            await asyncio.sleep(0.01)

    finally:
        sub_sock.setsockopt(zmq.LINGER, 0)
        sub_sock.close()

def process_message(message):
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


async def main():
    # Start listening to messages from player app and monitor the socket
    tasks = [
        asyncio.create_task(subscribe_to_messages( config['zmq']['ip_connect'], config['zmq']['port_player_pub'], process_message)),
        asyncio.create_task(handle_zmq_to_serial()),
        asyncio.create_task(handle_serial_to_zmq())
    ]
    await asyncio.gather(*tasks)

    logging.debug("Tasks created")


# Start the event loop
if __name__ == '__main__':
    asyncio.run(main())

# Close Serial Port
ser.close()
