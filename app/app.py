import zmq
import zmq.asyncio
import asyncio
import logging
import json
from modules.video_player import VideoPlayer
from modules.colorlight import ColorLightDisplay

class PlayerApp:
    def __init__(self, config):
        self.config = config
        self.ctx = zmq.asyncio.Context()
        self.sock = self.ctx.socket(zmq.REP)
        self.ws_queue = asyncio.Queue()


        #handle dummy config setting
        dummy_key_s = self.config['debug']['dummy_send']
        dummy_key = False
        if dummy_key_s == "True":
            dummy_key = True

        self.display = ColorLightDisplay(
            interface=config['interface'],
            brightness_level=config['brightness_level'],
            dummy= dummy_key
        )

        self.video_player = VideoPlayer(self.ws_queue, config['video_dir'], display_callback=self.display.display_frame)
        logging.basicConfig(level=self.get_log_level(config['debug']['log_level']))

    def get_log_level(self, level):
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return levels.get(level.upper(), logging.INFO)

    async def run(self):
        self.sock.bind(f"tcp://{self.config['zmq']['ip_player']}:{self.config['zmq']['port']}")

        while True:
            try:
                message = await self.sock.recv_string()
                await self.process_message(message)
            except Exception as e:
                logging.error(f"An error occurred: {str(e)}")
                await self.sock.send_string(f"An error occurred: {str(e)}")

    async def process_message(self, message):
        command = message.split(' ', 1)[0]
        logging.info(f"Received command: {command}")

        if command == 'play':
            video_index_or_name = message.split(' ', 1)[1] if len(message.split(' ', 1)) > 1 else None
            self.video_player.play(video_index_or_name)
            await self.sock.send_string("OK")

        elif command == 'pause':
            self.video_player.pause()
            await self.sock.send_string("OK")

        elif command == 'stop':
            self.video_player.stop()
            await self.sock.send_string("OK")

        elif command == 'resume':
            self.video_player.resume()
            await self.sock.send_string("OK")

        elif command == 'prev':
            self.video_player.prev_video()
            await self.sock.send_string("OK")

        elif command == 'next':
            self.video_player.next_video()
            await self.sock.send_string("OK")

        elif command == 'set_brightness':
            brightness = float(message.split(' ', 1)[1])
            logging.info(f"Received set_brightness: {brightness}")
            self.display.brightness_level = int(brightness)
            await self.sock.send_string("OK")

        elif command == 'get_brightness':
            brightness = float(self.display.brightness_level)
            await self.sock.send_string(str(brightness))
            logging.debug(f"Received get_brightness:, responded {brightness}")

        elif command == 'set_fps':
            fps = int(message.split(' ', 1)[1])
            self.video_player.fps = fps
            await self.sock.send_string("OK")

        elif command == 'get_fps':
            fps = self.video_player.fps
            await self.sock.send_string(str(fps))

        elif command == 'set_playlist':
            #  self.video_player.stop()
            #  self.video_player.load_playlist()
            await self.sock.send_string("OK")

        else:
            await self.sock.send_string("Unknown command")
            logging.warning("Unknown command received")


def load_config(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config


if __name__ == "__main__":
    config = load_config('config/config.json')
    app = PlayerApp(config)
    asyncio.run(app.run())

