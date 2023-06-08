import logging
import logging.handlers
import threading
import time
import array

from queue import Queue
from ola.ClientWrapper import ClientWrapper
from ola.OlaClient import OlaClient

from udp_server import UDPServer
from dmx import OlaThread
from ww_utils import WWFile, PlayMode

TICK_INTERVAL = 60  # in ms

localIP    = "192.168.0.25"
localPort  = 7000
universe   = 1
loop_count = 0
num_leds   = 14

#############################################
#LOGGING
logger = logging.getLogger('my_logger')
logger.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler('aperol.log', maxBytes=1024*1024, backupCount=10)
handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

handler.setFormatter(formatter)

logger.addHandler(handler)
logger.addHandler(console_handler)
#############################################

semaphore = threading.Semaphore()

wrapper = ClientWrapper()
udp_server = UDPServer(localIP, localPort, semaphore)

animation = WWFile('filename.ww', PlayMode.LOOP)

def PatchPortCallback(status):
  if status.Succeeded():
    logger.debug('OLA Patch Port Success!')
  else:
    logger.debug('OLA Patch Error: %s' % status.message)

def DmxSent(state):
  if not state.Succeeded():
    logger.debug("OLA fail to send DMX")
    wrapper.Stop()

def convert_data_to_dmx(data):
    dmx_data = array.array('B')
    for i in range(0, len(data), 3):
        dmx_data.append(data[i])
    return dmx_data

def calculate_frame():

    wrapper.AddEvent(TICK_INTERVAL, calculate_frame)

    #  data = [] # Code to get data
    if animation is not None:
        animation.update()
        data = game.animation.get_next_frame()

    dmx_data = convert_data_to_dmx(data)

    try:
        wrapper.Client().SendDmx(1, dmx_data, DmxSent)
    except  Exception as e:
        logger.error('Error: '+ str(e))

def main():
  udp_server.start()

  client = wrapper.Client()
  client.PatchPort(2, 1, True, OlaClient.PATCH, universe, PatchPortCallback)
  wrapper.AddEvent(TICK_INTERVAL, calculate_frame)
  wrapper.Run()

if __name__ == '__main__':
  main()

