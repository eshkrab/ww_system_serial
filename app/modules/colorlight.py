import socket
import numpy as np
from collections import deque
import threading
import time
import platform  

if platform.system() == "Darwin":
    from scapy.all import *

# Colorlight protocol constants
#  SRC_MAC = b'\x22\x22\x33\x44\x55\x66'
#  DST_MAC = b'\x11\x22\x33\x44\x55\x66'
#  BRIGHTNESS_LEVEL = 0xc1
#  #  BRIGHTNESS_LEVEL = 0xff  # 100% brightness
#  ETHERTYPE_DISPLAY_FRAME = 0x0107
#  ETHERTYPE_PIXEL_DATA_FRAME_BASE = 0x5500
#  INTERFACE = "eth0"  # Replace with your network interface name

class ColorLightDisplay:
    def __init__(
        self,
        interface: str,
        frame_queue = None,
        dummy: bool = False,
        src_mac: bytes = b"\x22\x22\x33\x44\x55\x66",
        dst_mac: bytes = b"\x11\x22\x33\x44\x55\x66",
        fps: int = 60,
        brightness_level: int = 0xC1,
        ether_type_display_frame: int = 0x0107,
        ether_type_pixel_data_frame_base: int = 0x5500,
    ):
        self.frame_queue = frame_queue
        self.interface = interface
        #  self.control_event                    = control_event
        self.src_mac = src_mac
        self.dst_mac = dst_mac
        self.fps = fps
        self.brightness_level = brightness_level
        self.ether_type_display_frame = ether_type_display_frame
        self.ether_type_pixel_data_frame_base = ether_type_pixel_data_frame_base

        self.dummy = dummy
        self.px_width = 64
        self.px_height = 64
        self.display_thread = None

        if not self.dummy:
            if platform.system() == "Darwin":
               # macOS
               self.raw_socket = None
            else:
               # Linux
               self.raw_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
               self.raw_socket.bind((self.interface, 0))

        #  self.display_thread.start()

    def __del__(self):
        if not self.dummy and self.raw_socket:
            self.raw_socket.close()

    def __enter__(self):
        return self

    #  def __exit__(self, exc_type, exc_value, traceback):
    #      self.raw_socket.close()

    def build_display_frame_package(self, brightness: int) -> bytes:
        length = 98
        header = self.ether_type_display_frame.to_bytes(2, "big")
        payload = bytearray([0x00] * (length - 2))
        payload[21] = brightness
        payload[22] = 5
        payload[24] = brightness
        payload[25] = brightness
        payload[26] = brightness

        return header + payload

    def build_set_brightness_frame_package(self, brightness: int) -> bytes:
        #  ethertype_set_brightness_frame = 0x0A00 | brightness
        ethertype_set_brightness_frame = (0x0A << 8) | brightness
        #  print(hex( ethertype_set_brightness_frame))
        ethertype = ethertype_set_brightness_frame + brightness

        length = 63
        header = ethertype.to_bytes(2, "big")
        payload = bytearray([0x00] * (length - 2))
        payload[0] = brightness
        #  payload[1] = brightness
        payload[1] = brightness
        payload[2] = 0xFF

        return header + payload

    def build_pixel_data_package(
        self, row_number: int, pixel_offset: int, pixel_data: bytes
    ) -> bytes:
        ether_type = self.ether_type_pixel_data_frame_base | (row_number >> 8)
        header = ether_type.to_bytes(2, "big")
        row_number_lsb = (row_number & 0xFF).to_bytes(1, "big")
        pixel_offset_msb = (pixel_offset >> 8).to_bytes(1, "big")
        pixel_offset_lsb = (pixel_offset & 0xFF).to_bytes(1, "big")
        pixel_count = len(pixel_data) // 3
        pixel_count_msb = (pixel_count >> 8).to_bytes(1, "big")
        pixel_count_lsb = (pixel_count & 0xFF).to_bytes(1, "big")
        data = bytearray([0x08, 0x88])

        payload = (
            header
            + row_number_lsb
            + pixel_offset_msb
            + pixel_offset_lsb
            + pixel_count_msb
            + pixel_count_lsb
            + data
            + pixel_data
        )

        return payload

    def send_raw_socket_package(self, package: bytes) -> None:
        eth_frame = self.dst_mac + self.src_mac + package

        if not self.dummy:
            if platform.system() == "Darwin":
                # macOS
                sendp(eth_frame, self.interface)
            else:
                # Linux
                self.raw_socket.send(eth_frame)

    def process_frame(self, frame: np.ndarray) -> list:
        height, width, _ = frame.shape
        pixel_packages = []

        for row in range(height):
            row_data = frame[row].tobytes()
            pixel_package = self.build_pixel_data_package(row, 0, row_data)
            pixel_packages.append(pixel_package)

        return pixel_packages

    #  def display_frame(self, frame: np.ndarray, brightness: int) -> None:
    def display_frame(self, frame: np.ndarray) -> None:
        brightness = self.brightness_level

        display_frame_package = self.build_display_frame_package(brightness)
        set_brightness_frame_package = self.build_set_brightness_frame_package(
            brightness
        )

        # Send the Set Brightness Frame package
        self.send_raw_socket_package(set_brightness_frame_package)
        self.send_raw_socket_package(set_brightness_frame_package)

        # Process and send the Pixel Data packages
        pixel_packages = self.process_frame(frame)
        for pixel_package in pixel_packages:
            self.send_raw_socket_package(pixel_package)
            self.send_raw_socket_package(pixel_package)

        #  Send the Display Frame package twice, doesn't work otherwise
        self.send_raw_socket_package(display_frame_package)
        self.send_raw_socket_package(display_frame_package)

    def clear_frame(
        self,
    ) -> None:
        zeros = np.zeros((self.px_height, self.px_width, 3), dtype=np.uint8)
        b = self.brightness_level
        self.brightness_level = 0
        self.display_frame(zeros)
        self.display_frame(zeros)
        self.display_frame(zeros)

        self.brightness_level = b
        print("clearedred")

    def display_loop(self):
        while True:
            #  # Check if control_event is set
            #  if self.control_event.is_set():
            #      # Pause the loop and wait for control_event to be cleared
            #      self.control_event.wait()
            #      time.sleep(0.001)
            #
            # Get frame from the frame queue
            if not self.frame_queue:
                time.sleep(0.001)
                continue

            if self.frame_queue:
                frame = self.frame_queue.popleft()
                self.display_frame(frame)

            # Sleep for a small amount of time
            time.sleep(1 / self.fps)

    #  def display_video(self, brightness, loop, fps: int = self.fps) -> None:
    #      time_delay = 1/self.fps
    #      video_capture = cv2.VideoCapture(self.video_file)
    #
    #      while video_capture.isOpened():
    #          ret, frame = video_capture.read()
    #          if ret:
    #              self.display_frame(frame, brightness)
    #
    #              # Adjust the sleep time to match the desired frame rate (30 FPS in this case)
    #              time.sleep(time_delay)
    #          else:
    #              video_capture.release() # Release the video capture object
    #              if loop:
    #                video_capture = cv2.VideoCapture(self.video_file)
    #              else:
    #                  break
