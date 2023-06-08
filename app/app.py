from os import name
import zmq
import zmq.asyncio
import asyncio
import logging
import json
#  from modules.video_player import VideoPlayer, VideoPlayerState, VideoPlayerMode
from modules.ww_player import WWVideoPlayer, VideoPlayerState, VideoPlayerMode
from modules.colorlight import ColorLightDisplay

class PlayerApp:
    def __init__(self, config):
        self.config = config
        self.ctx = zmq.asyncio.Context()
        self.sock = self.ctx.socket(zmq.REP)
        self.sock.setsockopt(zmq.RECONNECT_IVL, 1000)  # set reconnect interval to 1s
        self.sock.setsockopt(zmq.RECONNECT_IVL_MAX, 5000)  # set max reconnect interval to 5s
        self.ws_queue = asyncio.Queue()

        self.command_dict = {
            "play": self.play,
            "pause": self.pause,
            "stop": self.stop,
            "restart": self.restart,
            "prev": self.prev,
            "next": self.next,
            "get_state": self.get_state,
            "set_brightness": self.set_brightness,
            "get_brightness": self.get_brightness,
            "repeat": self.repeat,
            "repeat_one": self.repeat_one,
            "repeat_none": self.repeat_none,
            #  "get_mode": self.get_mode,
            "set_fps": self.set_fps,
            "get_fps": self.get_fps,
            "get_current_media": self.get_current_video,
            #  "set_playlist": self.set_playlist
        }


        #handle dummy config setting
        dummy_key_s = self.config['debug']['dummy_send']
        dummy_key = False
        if dummy_key_s == "True":
            dummy_key = True

        #  self.display = ColorLightDisplay(
        #      interface=config['interface'],
        #      brightness_level=config['brightness_level'],
        #      dummy= dummy_key
        #  )

        #  self.video_player = VideoPlayer(self.ws_queue, config['video_dir'], display_callback=self.display.display_frame)

        self.video_player = WWVideoPlayer(self.ws_queue, config['video_dir'], )

        logging.basicConfig(level=self.get_log_level(config['debug']['log_level']))

    async def play(self, params):
        self.video_player.play()
        await self.sock.send_string("OK")

    async def pause(self, params):
        self.video_player.pause()
        await self.sock.send_string("OK")

    async def stop(self, params):
        self.video_player.stop()
        await self.sock.send_string("OK")

    async def restart(self, params):
        logging.debug("Received restart")
        self.video_player.restart_video()
        await self.sock.send_string("OK")

    async def prev(self, params):
        logging.debug("Received prev")
        self.video_player.prev_video()
        await self.sock.send_string("OK")

    async def next(self, params):
        logging.debug("Received next")
        self.video_player.next_video()
        await self.sock.send_string("OK")
        

    async def get_state(self, params):
        state = "playing" if self.video_player.state == VideoPlayerState.PLAYING else "paused"
        if self.video_player.state == VideoPlayerState.STOPPED:
            state = "stopped"
            logging.debug("Received get_state: " + state)
        await self.sock.send_string(str(state))

    async def set_brightness(self, params):
        logging.debug("Received set_brightness")
        brightness = float(params[0]) if params else None
        if brightness is not None:
            #  self.display.brightness_level = int(brightness)
            await self.sock.send_string("OK")

    async def get_brightness(self, params):
        await self.sock.send_string(str(50))

    async def set_fps(self, params):
        fps = int(float(params[0])) if params else None
        if fps is not None:
            self.video_player.fps = fps
            await self.sock.send_string("OK")
    
    async def get_fps(self, params):
        await self.sock.send_string(str(self.video_player.fps))

    async def repeat(self, params):
        logging.debug("Received repeat")
        self.video_player.mode = VideoPlayerMode.REPEAT
        await self.sock.send_string("OK")

    async def repeat_one(self, params):
        logging.debug("Received repeat_one")
        self.video_player.mode = VideoPlayerMode.REPEAT_ONE
        await self.sock.send_string("OK")

    async def repeat_none(self, params):
        logging.debug("Received repeat_none")
        self.video_player.mode = VideoPlayerMode.REPEAT_NONE
        await self.sock.send_string("OK")

    async def get_current_video(self, params):
        #return current video name
        await self.sock.send_string(self.video_player.get_current_video_name())
        #  await self.sock.send_string(self.video_player.current_video)


    def get_log_level(self, level):
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return levels.get(level.upper(), logging.INFO)

    def reset_socket(self):
        # close the current socket
        self.sock.close()
        # create a new socket
        new_sock = self.ctx.socket(zmq.REP)
        new_sock.setsockopt(zmq.RECONNECT_IVL, 1000)  # set reconnect interval to 1s
        new_sock.setsockopt(zmq.RECONNECT_IVL_MAX, 5000)  # set max reconnect interval to 5s
        # bind the new socket
        try:
            new_sock.bind(f"tcp://{self.config['zmq']['ip_player']}:{self.config['zmq']['port']}")
        except zmq.ZMQError as zmq_error:
            logging.error(f"ZMQ Error occurred during socket reset: {str(zmq_error)}")
        return new_sock
 

    async def run(self):
        self.sock.bind(f"tcp://{self.config['zmq']['ip_player']}:{self.config['zmq']['port']}")

        while True:
            try:
                message = await self.sock.recv_string()
                await self.process_message(message)

            except zmq.ZMQError as zmq_error:
                logging.error(f"ZMQ Error occurred: {str(zmq_error)}")
                self.sock = self.reset_socket()  # reset the socket when a ZMQError occurs
        
            except Exception as e:
                logging.error(f"An error occurred: {str(e)}")
                await self.sock.send_string(f"An error occurred: {str(e)}")

    async def process_message(self, message):
        try:
            command = message.split(' ', 1)[0]
            logging.debug(f"Received command: {command}")

            if command in self.command_dict:  # check if command exists in command_dict
                await self.command_dict[command](message)
            else:
                await self.sock.send_string("Unknown command")
                logging.warning(f"Unknown command received: {command}")
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            await self.sock.send_string(f"Error processing message: {str(e)}")



def load_config(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    return config


if __name__ == "__main__":
    config = load_config('config/config.json')
    app = PlayerApp(config)
    asyncio.run(app.run())

