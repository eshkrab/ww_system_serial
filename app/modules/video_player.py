import os
import cv2
import glob
import time
import json
import threading
import numpy as np
from enum import Enum
from collections import deque
import queue
from modules.colorlight import ColorLightDisplay

MAX_Q_LEN = 100


class VideoPlayerState(Enum):
    PLAYING = 1
    STOPPED = 2
    PAUSED = 3


class VideoPlayerPlayMode(Enum):
    LOOP = 1
    HOLD = 2
    ZERO = 3


class VideoPlayer:
    def __init__(self, ws_queue, video_dir: str):
        self.video_dir = video_dir
        self.ws_queue = ws_queue
        self.video_queue = deque(maxlen=MAX_Q_LEN)
        self.frame_queue = deque(maxlen=10)
        self.state = VideoPlayerState.PLAYING
        self.mode = VideoPlayerPlayMode.LOOP
        self.current_video = None
        self.playlist = []
        self.playlist_path = video_dir + "/playlist.json"
        self.lock = threading.Lock()

        self.display = ColorLightDisplay(
            frame_queue=self.frame_queue,
            interface="en7",
            fps=30,
            brightness_level=50,
            src_mac=b"\x22\x22\x33\x44\x55\x66",
            dst_mac=b"\x11\x22\x33\x44\x55\x66",
            ether_type_display_frame=0x0107,
            ether_type_pixel_data_frame_base=0x5500,
        )

        self.populate_video_queue()
        #  self.play()

    def play(self):
        #  with self.lock:
            self.state = VideoPlayerState.PLAYING
            # Create a new thread only if there is not one already running
            if (
                not hasattr(self, "playback_thread")
                or not self.playback_thread.is_alive()
            ):
                self.playback_thread = threading.Thread(target=self.playback_loop)
                self.playback_thread.start()

            for thread in threading.enumerate():
                print(thread.name)
    #  def play(self):
    #      if self.state == VideoPlayerState.STOPPED:
    #          self.playback_thread = threading.Thread(target=self.playback_loop)
    #          self.playback_thread.start()
    #          print('started thread')
    #
    #      self.state = VideoPlayerState.PLAYING

    def stop(self):
        #  with self.lock:
            self.state = VideoPlayerState.STOPPED
            self.playlist.clear()
            self.video_queue.clear()
            self.current_video = None

            for thread in threading.enumerate():
                print(thread.name)

            if self.playback_thread and self.playback_thread.is_alive():
                print("joined thread")
                self.playback_thread.join()
            else:
                print('thread aint alive')

    def pause(self):
        #  with self.lock:
            self.state = VideoPlayerState.PAUSED

    def populate_video_queue(self):
        if not os.path.exists(self.playlist_path):
            self.create_playlist_file()

        with open(self.playlist_path, "r") as f:
            playlist = json.load(f)

        self.mode = VideoPlayerPlayMode[playlist["mode"]]

        for video_path in playlist["playlist"]:
            item_data = {
                "video_path": self.video_dir + video_path,
                "playback_mode": self.mode,
            }
            self.playlist.append(item_data)
        print(self.playlist)

    def create_playlist_file(self):
        video_files = (
            glob.glob(os.path.join(self.video_dir, "*.mp4"))
            + glob.glob(os.path.join(self.video_dir, "*.mov"))
            + glob.glob(os.path.join(self.video_dir, "*.avi"))
        )

        playlist = {
            "mode": "LOOP",
            "playlist": [os.path.basename(video_file) for video_file in video_files],
        }

        with open(self.playlist_path, "w") as f:
            json.dump(playlist, f, indent=4)
            print("WROTE FILE")

    def playback_loop(self):
        while True:
            if self.state == VideoPlayerState.STOPPED:
                print('state is stopped')
                break

            elif self.state == VideoPlayerState.PAUSED:
                print('state is paused')
                time.sleep(0.01)
                continue

            elif self.state == VideoPlayerState.PLAYING:
                if not self.playlist:
                    self.populate_video_queue()

                if not self.video_queue:
                    self.video_queue.extend(self.playlist)

                if not self.current_video and self.video_queue:
                    # If there's no current video, pop the next one from the queue and load it
                    video_data = self.video_queue.popleft()
                    self.current_video = cv2.VideoCapture(video_data["video_path"])

                    if not self.current_video.isOpened():
                        print(f"Failed to open video: {video_data['video_path']}")
                        self.current_video = None
                        continue

                if self.current_video:
                    #  with self.lock:
                        # Read the next frame and put it on the frame queue and websocket queue
                        ret, frame = self.current_video.read()
                        if ret:
                            pass
                            #  self.frame_queue.append(frame)
                            self.display.display_frame(frame)
                            #  for i in range(0,2):
                            #      self.display.display_frame(frame)
                                #  time.sleep(0.001)
                            #  try:
                            #      self.ws_queue.put(frame, timeout=0.001)
                            #  except queue.Full:
                            #      pass
                        else:
                            # If there are no more frames in the current video, mark it as None
                            self.current_video.release()
                            self.current_video = None

            # Sleep for a small amount of time to avoid excessive CPU usage
            time.sleep(1 / self.display.fps)
