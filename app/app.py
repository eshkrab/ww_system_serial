import zmq
import zmq.asyncio
import asyncio
import logging

import json

from modules.video_player import VideoPlayer
from modules.colorlight import ColorLightDisplay

# Configuring logging
logging.basicConfig(level=logging.DEBUG)

def load_config(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config

config = load_config('config/config.json')

class PlayerApp:
    def __init__(self):
        self.ctx = zmq.asyncio.Context()
        self.sock = self.ctx.socket(zmq.REP)
        self.ws_queue = asyncio.Queue()

        self.display = ColorLightDisplay(
            interface=config['interface'],
            brightness_level=config['brightness_level'],
        )

        self.video_player = VideoPlayer(self.ws_queue, "content", display_callback=self.display.display_frame)

    async def run(self):
        self.sock.bind(f"tcp://{config['zmq']['ip']}:{config['zmq']['port']}")

        while True:
            try:
                # Receive a message from any client
                message = await self.sock.recv_string()

                # process the message
                command = message.split(' ', 1)[0]
                logging.info(f"Received command: {command}")

                if command == 'play':
                    self.video_player.play()
                    await self.sock.send_string("OK")

                elif command == 'pause':
                    self.video_player.pause()
                    await self.sock.send_string("OK")

                elif command == 'stop':
                    self.video_player.stop()
                    await self.sock.send_string("OK")

                elif command == 'resume':
                    self.video_player.play()
                    await self.sock.send_string("OK")

                elif command == 'set_brightness':
                    brightness = float(message.split(' ', 1)[1])
                    self.display.brightness_level = brightness
                    await self.sock.send_string("OK")

                elif command == 'get_brightness':
                    brightness = self.display.brightness_level
                    await self.sock.send_string(str(brightness))

                elif command == 'set_fps':
                    fps = float(message.split(' ', 1)[1])
                    self.video_player.fps = fps
                    await self.sock.send_string("OK")

                elif command == 'get_fps':
                    fps = self.video_player.fps
                    await self.sock.send_string(str(fps))

                else:
                    await self.sock.send_string("Unknown command")
                    logging.warning("Unknown command received")

            except Exception as e:
                logging.error(f"An error occurred: {str(e)}")
                await self.sock.send_string(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    app = PlayerApp()
    asyncio.run(app.run())

