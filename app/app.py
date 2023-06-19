import json
import logging
import serial
import asyncio
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

async def send_message_to_player(message):
    try:
        logging.debug(f"Publishing message: {message}")
        await pub_socket.send_string(message)
    except zmq.ZMQError as e:
        logging.error(f"ZMQError while publishing message: {e}")
        return -1

async def subscribe_to_player():
    logging.debug("Subscribing to Player")

    poller = zmq.Poller()
    poller.register(sub_socket, zmq.POLLIN)

    while True:
        logging.debug("Waiting for message from Player")
        socks = dict(poller.poll(100))

        # If there's a message on the socket, receive and process it
        logging.debug(f"socks: {socks}")

        if sub_socket in socks:
            message = sub_socket.recv()
            logging.debug(f"Received from Player: {message}")


        #  #  message = await sub_socket.recv_string()
        #  #  logging.debug(f"Received from Player: {message}")
        #
        #  # Process the received message
        #  message = message.split(" ")
        #  if message[0] == "state":
        #      player.state = message[1]
        #  elif message[0] == "mode":
        #      player.mode = message[1]
        #  elif message[0] == "brightness":
        #      brightness = float(message[1]) / 255.0
        #      player.brightness = float(brightness)
        #  elif message[0] == "fps":
        #      player.fps = int(message[1])
        #  elif message[0] == "current_media":
        #      player.current_media = message[1]
        #  else:
        #      logging.error(f"Unknown message from Player: {message}")
        #
        await asyncio.sleep(0.1)
        logging.debug(f"Player state: {player.state}")


async def handle_zmq_to_serial():
    while True:
        #  message = await socket.recv_string()
        message = "serial test"
        #  logging.debug(f"Received message from ZeroMQ: {message}")
        
        # Write the message to the serial port
        ser.write(message.encode())

async def handle_serial_to_zmq():
    while True:
        if ser.in_waiting:
            data = ser.readline().decode().strip()
            logging.debug(f"Received data from serial port: {data}")

            # Process the data or send it to ZeroMQ
            # Example: Send the data as a message to ZeroMQ
            #  await send_message_to_player(f"process_data {data}")
            #  logging.debug(f"Reply from player: {reply}")

# Example usage
async def example_usage():
    # Start listening to messages from player app
    asyncio.create_task(subscribe_to_player())
    # Start the ZeroMQ-to-Serial and Serial-to-ZeroMQ handlers
    tasks = [
        asyncio.create_task(handle_zmq_to_serial()),
        asyncio.create_task(handle_serial_to_zmq())
    ]
    await asyncio.gather(*tasks)

# Run the example usage in an event loop
async def main():
    await example_usage()

# Start the event loop
#  zmq.asyncio.install()
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    loop.run_until_complete(main())
finally:
    loop.close()            

