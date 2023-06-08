import struct
import os
from collections import deque
from enum import Enum

class PlayMode(Enum):
    HOLD = 1
    LOOP = 2

header_size = 13
chunk_size = 512

class WWFile:
    def __init__(self, filename, _play_mode=PlayMode.LOOP):
        self.filename = filename
        self.header = None
        self.framerate = None
        self.bpp = None
        self.num_strips = None
        self.num_pixels = None
        self.frame_size = None
        self.file_size = None
        self.current_frame = None
        self.bytes_loaded = 0
        self.frame_deque = deque()
        self.play_mode = _play_mode
        self.is_playing = False
        
        with open(self.filename, 'rb') as f:
            self.header = f.read(header_size)
            assert self.header[0] == 0 and self.header[1] == 0, "Invalid header"
            assert self.header[2:4] == b'WW', "Invalid header"
            assert self.header[4] == 0 and self.header[5] == 0, "Invalid header"
            assert self.header[11] == 0 and self.header[12] == 0, "Invalid header"
            
            self.framerate = self.header[6]
            self.bpp = self.header[7]
            self.num_strips = self.header[8]
            self.num_pixels = struct.unpack('>H', self.header[9:11])[0]
            self.frame_size = self.bpp * self.num_strips * self.num_pixels
            
            self.file_size = os.path.getsize(self.filename)


    def load_next_chunk(self, reload = False):
        with open(self.filename, 'rb') as f:
            if not reload:
                f.seek(len(self.header) + self.bytes_loaded)
            else:
                self.bytes_loaded = 0
                f.seek(len(self.header))

            chunk = f.read(chunk_size * self.frame_size)
            if not chunk:
                return

            self.bytes_loaded += len(chunk)

            byte_array = bytearray(chunk)
        
            for i in range(0, len(byte_array), self.frame_size):
                current_frame = byte_array[i:i+self.frame_size]
                self.frame_deque.append(current_frame)

    def get_next_frame(self):
        if len(self.frame_deque) > 0:
            frame = self.frame_deque.popleft()
        else:
            frame = bytearray(bytes(self.frame_size))
        return frame

    def update(self, reload = False):
        if reload:
            self.frame_deque.clear()
            self.load_next_chunk(reload = True)
        elif len(self.frame_deque) < 1:
            if (header_size + self.bytes_loaded) < self.file_size :
                #  print('LOAD NEXT CHUNK '+'bytes '+str(self.bytes_loaded) +' fs '+str(self.file_size))
                self.load_next_chunk()
            elif self.play_mode == PlayMode.LOOP:
                #  print("RELOADING")
                self.load_next_chunk(reload = True)

        if len(self.frame_deque) > 0:
            #  self.current_frame = self.get_next_frame()
            self.is_playing = True
        else:
            #  print('no frames in deque')
            self.current_frame = bytearray(bytes(self.frame_size))
            self.is_playing = False


        #  return byte_array
#  ########################3##
#  from collections import deque
#
#  # Initialize a deque with a fixed maximum size
#  ring_buffer = deque(maxlen=1024)
#
#  # Read data from a file and buffer it in the ring buffer
#  with open('data.txt', 'rb') as f:
#      while True:
#          data = f.read(1024)  # Read 1024 bytes at a time
#          if not data:
#              break
#          ring_buffer.extend(data)  # Add data to the end of the deque
#
#  # Process the data in the ring buffer
#  while ring_buffer:
#      data = ring_buffer.popleft()  # Remove and return the first element in the deque
#      # Process the data here...
#
