import json
import logging
import serial
import zmq.asyncio

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load configuration from JSON file
with open('config/config.json', 'r') as f:
    config = json.load(f)

# Set up ZeroMQ context and socket
ctx = zmq.asyncio.Context()
socket = ctx.socket(zmq.REQ)
socket.connect(f"tcp://{config['zmq']['ip_server']}:{config['zmq']['port']}")

# Set up Serial port
serial_port = config['serial_port']
serial_baudrate = config['serial_baudrate']
ser = serial.Serial(serial_port, serial_baudrate)

async def send_message_to_player(message):
    try:
        logging.debug(f"Sending message: {message}")
        await socket.send_string(message)
        reply = await socket.recv_string()
        return reply
    except zmq.ZMQError as e:
        logging.error(f"ZMQError while sending/receiving message: {e}")
        return -1

async def handle_zmq_to_serial():
    while True:
        message = await socket.recv_string()
        logging.debug(f"Received message from ZeroMQ: {message}")
        
        # Write the message to the serial port
        ser.write(message.encode())

async def handle_serial_to_zmq():
    while True:
        if ser.in_waiting > 0:
            data = ser.readline().decode().strip()
            logging.debug(f"Received data from serial port: {data}")

            # Process the data or send it to ZeroMQ
            # Example: Send the data as a message to ZeroMQ
            reply = await send_message_to_player(f"process_data {data}")
            logging.debug(f"Reply from player: {reply}")

# Example usage
async def example_usage():
    # Start the ZeroMQ-to-Serial and Serial-to-ZeroMQ handlers
    tasks = [
        handle_zmq_to_serial(),
        handle_serial_to_zmq()
    ]
    await asyncio.gather(*tasks)

# Run the example usage in an event loop
async def main():
    await example_usage()

# Start the event loop
zmq.asyncio.install()
loop = zmq.asyncio.ZMQEventLoop()
asyncio.set_event_loop(loop)
loop.run_until_complete(main())

