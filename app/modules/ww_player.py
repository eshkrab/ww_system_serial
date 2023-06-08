import os
import cv2
import glob
import time
import array
import json
import threading
import logging
import socket
import numpy as np
from enum import Enum
from collections import deque
from typing import Callable, Optional, List, Dict

# Import OLA dependencies
from queue import Queue
from ola.ClientWrapper import ClientWrapper
from ola.OlaClient import OlaClient

from modules.ww_utils import WWFile

class VideoPlayerState(Enum):
    PLAYING = 1
    STOPPED = 2
    PAUSED = 3

class VideoPlayerMode(Enum):
    REPEAT = 1
    REPEAT_ONE = 2
    REPEAT_NONE = 3

class WWVideoPlayer:
    def __init__(self, ws_queue, video_dir: str, fps: int = 30,
                 display_callback: Optional[Callable[[np.array], None]] = None):
        self.video_dir = video_dir
        self.ws_queue = ws_queue
        self.fps = fps
        self.state = VideoPlayerState.STOPPED
        self.mode = VideoPlayerMode.REPEAT
        self.current_video = None
        self.playlist: List[Dict[str, Union[str, VideoPlayerMode]]] = []
        self.playlist_path = os.path.join(video_dir, "playlist.json")
        self.lock = threading.Lock()
        self.current_video_index = 0
        self.display_callback = display_callback
        self.ola_thread = None
        self.wrapper = None
        self.client = None
        # Create a TCP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.load_playlist()

    def get_current_video_name(self):
        filepath = self.playlist[self.current_video_index]["filepath"]
        return os.path.basename(filepath)

    def play(self):
        with self.lock:
            if self.state != VideoPlayerState.PLAYING:
                self.state = VideoPlayerState.PLAYING
                if not self.ola_thread or not self.ola_thread.is_alive():
                    self.ola_thread = threading.Thread(target=self.ola_integration_loop)
                    self.ola_thread.start()

    def stop(self):
        with self.lock:
            if self.state != VideoPlayerState.STOPPED:
                self.state = VideoPlayerState.STOPPED
                self.playlist.clear()
                self.current_video = None
                if self.ola_thread and self.ola_thread.is_alive():
                    self.ola_thread.join()

    def pause(self):
        with self.lock:
            if self.state != VideoPlayerState.PAUSED:
                self.state = VideoPlayerState.PAUSED

    def resume(self):
        with self.lock:
            if self.state == VideoPlayerState.PAUSED:
                self.play()

    def next_video(self):
        with self.lock:
            self.current_video_index = (self.current_video_index + 1) % len(self.playlist)
            self.load_video(self.current_video_index)

    def prev_video(self):
        with self.lock:
            self.current_video_index = (self.current_video_index - 1) % len(self.playlist)
            self.load_video(self.current_video_index)

    def restart_video(self):
        with self.lock:
            self.load_video(self.current_video_index)

    def load_video(self, index: int):
        with self.lock:
            self.current_video_index = index
            # Load WW animation file here
            animation_file = self.playlist[self.current_video_index]['filepath']
            self.current_video = WWFile(animation_file)

    def load_playlist(self):
        if not os.path.exists(self.playlist_path):
            self.create_playlist_file()

        with open(self.playlist_path, "r") as f:
            playlist = json.load(f)
        self.mode = VideoPlayerMode[playlist["mode"].upper()]
        self.playlist = [
            {
                "filepath": video_info['filepath'],
                "name": video_info['name'],
                "thumbnail": video_info['thumbnail']
            }
            for video_info in playlist["playlist"]
        ]

    def create_thumbnail_path(self, video_file):
        video_filename = os.path.basename(video_file)
        thumbnail_filename = f"{os.path.splitext(video_filename)[0]}_thumbnail.jpg"
        thumbnail_path = os.path.join(self.video_dir, thumbnail_filename)

        if not os.path.exists(thumbnail_path):
            # Generate thumbnail if it doesn't exist
            clip = cv2.VideoCapture(video_file)
            ret, frame = clip.read()
            if ret:
                cv2.imwrite(thumbnail_path, frame)  # Save the frame as thumbnail image
            clip.release()

        return thumbnail_filename

    def create_playlist_file(self):
        video_files = glob.glob(os.path.join(self.video_dir, "*.ww"))
        playlist = {
            "mode": self.mode.name,
            "playlist": [
                {
                    "name": os.path.basename(video_file),
                    "filepath": video_file,
                    "thumbnail": self.create_thumbnail_path(video_file)
                }
                for video_file in video_files
            ]
        }
        with open(self.playlist_path, "w") as f:
            json.dump(playlist, f, indent=4)

    def ola_integration_loop(self):
        # Bind the socket to a specific address and port
        host = '192.168.86.147'  # Example IP address
        port = 9010  # Example port number
        self.socket.connect((host, port))
        self.wrapper = ClientWrapper()


        self.client = self.wrapper.Client()
        #  self.client._socket = self.socket
# create a tcp socket with 'ola' and '9010'


        self.client.PatchPort(2, 1, True, OlaClient.PATCH, 1, self.ola_patch_port_callback)
        #  self.wrapper.Run()

    def ola_patch_port_callback(self, status):
        if status.Succeeded():
            logging.debug('OLA Patch Port Success!')
            self.start_ola_integration()
        else:
            logging.debug('OLA Patch Error: %s' % status.message)

    def start_ola_integration(self):
        if self.wrapper:
            self.wrapper.AddEvent(1000 / self.fps, self.ola_frame_update)
            self.wrapper.Run()

    def ola_frame_update(self):
        if self.wrapper:
            self.wrapper.AddEvent(1000 / self.fps, self.ola_frame_update)
        with self.lock:
            if self.state == VideoPlayerState.PLAYING:
                if self.current_video:
                    self.current_video.update()
                    frame = self.current_video.get_next_frame()
                    if frame is not None:
                        ola_data = self.convert_frame_to_ola_data(frame)
                        self.send_ola_data(ola_data)

    def convert_frame_to_ola_data(self, frame):
        # Convert WW animation frame to OLA data format
        # Implement your conversion logic here
        dmx_data = array.array('B')
        for i in range(0, len(frame), 3):
            dmx_data.append(frame[i])
        return dmx_data
        #  pass

    def send_ola_data(self, data):
        # Send OLA data to the appropriate channel/universe
        # Implement your OLA sending logic here
        if self.wrapper:
            self.client.SendDmx(1, data, self.DmxSent)
        pass

    def DmxSent(state):
      if not state.Succeeded():
        logger.debug("OLA fail to send DMX")
        self.wrapper.Stop()

