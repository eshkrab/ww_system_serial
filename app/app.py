import zmq
import zmq.asyncio
import asyncio

from modules/video_player import VideoPlayer
from modules/colorlight import ColorLightDisplay


class PlayerApp:

    def __init__(self):
        self.ctx = zmq.asyncio.Context()
        self.sock = self.ctx.socket(zmq.REP)
        self.video_player = VideoPlayer()
        self.display = ColorLightDisplay(
            frame_queue=self.frame_queue,
            interface="en7",
            brightness_level=50,
        )

    async def run(self):
        self.sock.bind("tcp://127.0.0.1:5555")  # bind the socket to a specific address

        while True:
            # Receive a message from any client
            message = await self.sock.recv_string()

            # process the message
            command = message.split(' ', 1)[0]
            if command == 'play':
                self.video_player.play()

            elif command == 'pause':
                self.video_player.pause()

            elif command == 'stop':
                self.video_player.stop()

            elif command == 'resume':
                self.video_player.play()

            elif command == 'set_brightness':
                brightness = float(message.split(' ', 1)[1])
                self.color_light.set_brightness(brightness)
                await self.sock.send_string("OK")

            elif command == 'get_brightness':
                brightness = self.color_light.get_brightness()
                await self.sock.send_string(str(brightness))

            elif command == 'set_fps':
                fps = float(message.split(' ', 1)[1])
                self.video_player.set_fps(fps)
                await self.sock.send_string("OK")

            elif command == 'get_fps':
                fps = self.video_player.get_fps()
                await self.sock.send_string(str(fps))

            else:
                await self.sock.send_string("Unknown command")


if __name__ == "__main__":
    app = PlayerApp()
    asyncio.run(app.run())

