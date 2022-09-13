import string, time
import argparse
import os
import json
import logging
import datetime
import sys
import traceback
import threading
import glob
import evdev
from evdev import InputDevice, categorize, ecodes  


from omxplayer.player import OMXPlayer
from pathlib import Path
from time import sleep

import sys, traceback

clip_player = False
paths = {}
flags = {}
flags["showing_no_drive_screen"] = False
flags["clip_is_playing"] = False
loop_index = 0
warmup_time = 0.5
logger = logging.getLogger()

# Scancode for the HID input coming from the barcode reader

scancodes = {
    # Scancode: ASCIICode
    0: None, 1: u'ESC', 2: u'1', 3: u'2', 4: u'3', 5: u'4', 6: u'5', 7: u'6', 8: u'7', 9: u'8',
    10: u'9', 11: u'0', 12: u'-', 13: u'=', 14: u'BKSP', 15: u'TAB', 16: u'q', 17: u'w', 18: u'e', 19: u'r',
    20: u't', 21: u'y', 22: u'u', 23: u'i', 24: u'o', 25: u'p', 26: u'[', 27: u']', 28: u'CRLF', 29: u'LCTRL',
    30: u'a', 31: u's', 32: u'd', 33: u'f', 34: u'g', 35: u'h', 36: u'j', 37: u'k', 38: u'l', 39: u';',
    40: u'"', 41: u'`', 42: u'LSHFT', 43: u'\\', 44: u'z', 45: u'x', 46: u'c', 47: u'v', 48: u'b', 49: u'n',
    50: u'm', 51: u',', 52: u'.', 53: u'/', 54: u'RSHFT', 56: u'LALT', 57: u' ', 100: u'RALT'
}


capscodes = {
    0: None, 1: u'ESC', 2: u'1', 3: u'2', 4: u'3', 5: u'4', 6: u'5', 7: u'6', 8: u'7', 9: u'8',
    10: u'9', 11: u'0', 12: u'-', 13: u'=', 14: u'BKSP', 15: u'TAB', 16: u'Q', 17: u'W', 18: u'E', 19: u'R',
    20: u'T', 21: u'Y', 22: u'U', 23: u'I', 24: u'O', 25: u'P', 26: u'{', 27: u'}', 28: u'CRLF', 29: u'LCTRL',
    30: u'A', 31: u'S', 32: u'D', 33: u'F', 34: u'G', 35: u'H', 36: u'J', 37: u'K', 38: u'L', 39: u':',
    40: u'\'', 41: u'~', 42: u'LSHFT', 43: u'|', 44: u'Z', 45: u'X', 46: u'C', 47: u'V', 48: u'B', 49: u'N',
    50: u'M', 51: u'<', 52: u'>', 53: u'?', 54: u'RSHFT', 56: u'LALT',  57: u' ', 100: u'RALT'
}
#setup vars
input_buffer = ''
caps = True

def show_background_screen():
  global paths, logger
  # os.system("sudo pkill fbi")
  os.system("sudo fbi -T 2 -d /dev/fb0 -noverbose -a {}".format(paths["background_path"]))

def show_no_drive_screen():
  global paths, flags, logger
  # Put up the no drive screen
  if flags["showing_no_drive_screen"] == False:
    logger.info("showing_no_drive_screen == False")
    flags["showing_no_drive_screen"] = True
    os.system("sudo pkill fbi")
    os.system("sudo fbi -T 2 -d /dev/fb0 -noverbose -a {}".format(paths["no_loop_image_path"]))
    sleep(3)
    threading.Thread(target=play_loop,).start()
  else:
    logger.info("showing_no_drive_screen == True")
    sleep(3)
    threading.Thread(target=play_loop,).start()

def show_no_loop_screen():
  global paths
  threading.Thread(target=play_clip, args=(paths["no_loop_video_path"],)).start()
  # Put up the no video screen
  # os.system("sudo pkill fbi")
  # os.system("sudo fbi -T 2 -d /dev/fb0 -noverbose -a {}".format(paths["no_loop_image_path"]))
  # sleep(3)
  # show_background_screen()
  # threading.Thread(target=play_loop,).start()

def show_no_video_screen():
  global paths
  threading.Thread(target=play_clip, args=(paths["no_video_video_path"],)).start()
  # #play a clip instead of showing a video  
  # os.system("sudo fbi -T 2 -d /dev/fb0 -noverbose -a {}".format(paths["no_video_image_path"]))
  # sleep(3)
  # show_background_screen()
  # threading.Thread(target=play_loop,).start()

def play_clip(file_path):
  global clip_player, flags, warmup_time, paths, logger

  if (len(glob.glob(file_path)) == 0):
    # Couldn't find the video. Show the no video image
    print("VIDEO NOT FOUND: " + file_path)
    show_no_video_screen()
    return
  try:
    print("Threaded, playing clip on demand")
    # Stop any other playing clips
    stop_clip()
    flags["clip_is_playing"] = True
    
    print("File path is {}".format(file_path))
    # Load the on-demand clip
    clip_player = OMXPlayer(file_path)
    # let it warm up
    sleep(warmup_time)
    # play it using the blocking, synchronous play_sync call. It will poll until it's done.
    clip_player.play_sync()
    # okay, that's over now! clean up and loop again
    print("done playing clip")
    stop_clip()
    threading.Thread(target=play_loop,).start()
  except Exception:
    # Something blew up - clean up any omxplayers
    logger.info("Something failed in a thread, trying to handle it gracefully")
    traceback.print_exc(file=sys.stdout)
    os.system("pkill omxplayer")
    sys.exit(0)

def play_loop():
  global clip_player, flags, loop_index, paths, warmup_time, flags, logger
  if (os.path.exists(paths["loop_video_path"]) == False):
    # Couldn't find the thumbdrive. Show the no videos image
    show_no_drive_screen()
    return
  elif (len(glob.glob(paths["video_path"] + "/*.mp4")) == 0):
    # Couldn't find any product videos. Show the no videos image
    # We could show loops here if we had them but the decision was NOT to 
    # Based on emails from 2018-12-07
    show_no_drive_screen()
    return
  elif (len(glob.glob(paths["loop_video_path"] + "/*.mp4")) == 0):
    # Couldn't find the video. Show the no video image
    show_no_loop_screen()
    return
  try:
    print("Threaded, playing loop on demand")
    #os.system("sudo pkill fbi")
    show_background_screen()
    flags["showing_no_drive_screen"] = False
    loopfiles = []
    for file in glob.glob(paths["loop_video_path"] + "/*.mp4"):
      loopfiles.append(file)

    # print(loopfiles)
    loopfiles.sort()

    while True:
      if flags["clip_is_playing"]:
        # if the clip is playing, break out of this loop, which terminates the thread
        break

      # Stop any other playing clips
      stop_clip()
      print("File path is {}".format(loopfiles[loop_index]))
      # Load the on-demand clip
      clip_player = OMXPlayer(loopfiles[loop_index])
      # let it warm up
      sleep(warmup_time)
      # play it using the blocking, synchronous play_sync call. It will poll until it's done.
      clip_player.play_sync()
      # okay, that's over now! clean up and loop again

      print("done playing loop, up the index and play the next")
      
      # Increment the loop index, roll over if we hit the max
      loop_index += 1
      if loop_index == len(loopfiles):
        loop_index = 0
  except Exception:
    # Something blew up - clean up any omxplayers
    logger.info("Something failed in a thread, trying to handle it gracefully")
    traceback.print_exc(file=sys.stdout)
    os.system("pkill omxplayer")
    os.system("sudo pkill fbi")
    sys.exit(0)

def stop_clip():
  global clip_player, flags
  # Quit any other clips playing
  if clip_player != False:
    clip_player.quit()
    sleep(0.1)
    clip_player = False
  os.system("pkill omxplayer")
  flags["clip_is_playing"] = False

def main():
  global paths, caps, input_buffer, logger
  try:
    
    parser = argparse.ArgumentParser(description='PiKiosk barcode watcher - waits for barcode input and plays videos on demand')
    def auto_int(x):
        return int(x, 0)
    parser.add_argument('-s', '--settings', type=argparse.FileType('r'),
                        default=os.path.join(os.path.dirname(__file__),
                                             'setting_defaults.json'),
                        help='pikiosk settings dict file to read. If unspecified, defaults are used')

    logging.basicConfig(level=logging.WARNING)

    args = parser.parse_args()
    settings_dict = json.load(args.settings)
    logger.info(settings_dict)

    if 'video_path' in settings_dict:
      paths["video_path"] = settings_dict['video_path']
    else:
      paths["video_path"] = "./videos/"

    if 'loop_video_path' in settings_dict:
      paths["loop_video_path"] = settings_dict['loop_video_path']
    else:
      paths["loop_video_path"] = "001.mp4"

    if 'background_path' in settings_dict:
      paths["background_path"] = settings_dict['background_path']
    else:
      paths["background_path"] = "./background.png"

    if 'no_video_image_path' in settings_dict:
      paths["no_video_image_path"] = settings_dict['no_video_image_path']
    else:
      paths["no_video_image_path"] = "./NoMatch.jpg"

    if 'no_video_video_path' in settings_dict:
      paths["no_video_video_path"] = settings_dict['no_video_video_path']
    else:
      paths["no_video_video_path"] = "./NoMatch.mp4"

    if 'no_loop_image_path' in settings_dict:
      paths["no_loop_image_path"] = settings_dict['no_loop_image_path']
    else:
      paths["no_loop_image_path"] = "./NoLoop.jpg"

    if 'no_loop_video_path' in settings_dict:
      paths["no_loop_video_path"] = settings_dict['no_loop_video_path']
    else:
      paths["no_loop_video_path"] = "./NoLoop.mp4"

    if 'no_files_image_path' in settings_dict:
      paths["no_files_image_path"] = settings_dict['no_files_image_path']
    else:
      paths["no_files_image_path"] = "./NoFiles.jpg"

    print ("Looping main vid, awaiting barcode input")

    # Put up the splash screen
    sleep(0.1)
    show_background_screen()

    # Play the loop, threaded. Starting a clip will kill this thread.
    threading.Thread(target=play_loop,).start()


    # This is the heart of the script, like the loop in arduino. 
    # We just sit in this thing and wait for input over and over, 
    #   spawning threads as needed to play clips.
    dev = InputDevice('/dev/input/event0')
    dev.grab()

    while True:
      #loop
      for event in dev.read_loop():
        if event.type == ecodes.EV_KEY:
          data = categorize(event)  # Save the event temporarily to introspect it
          if data.scancode == 42:
            if data.keystate == 1:
              caps = True
            if data.keystate == 0:
              caps = False
          if data.keystate == 1:  # Down events only
            if caps:
              key_lookup = u'{}'.format(capscodes.get(data.scancode)) or u'UNKNOWN:[{}]'.format(data.scancode)  # Lookup or return UNKNOWN:XX
            else:
              key_lookup = u'{}'.format(scancodes.get(data.scancode)) or u'UNKNOWN:[{}]'.format(data.scancode)  # Lookup or return UNKNOWN:XX
            if (data.scancode != 42) and (data.scancode != 28):
              input_buffer += key_lookup  
            if(data.scancode == 28):
              print("You scanned the code: {}".format(input_buffer))
              # compose the path to the file
              file_path = paths["video_path"] + input_buffer + ".mp4"
              # TODO CHECK IF THE FILE EXISTS
              threading.Thread(target=play_clip, args=(file_path,)).start()
              input_buffer = ''
      
        
  except KeyboardInterrupt:
    # The user hit ctrl-c - clean up what we can and get out of dodge
    print("PiKiosk shutdown requested")
    if clip_player:
      clip_player.quit()
    os.system("pkill omxplayer")
    os.system("sudo pkill fbi")

  except Exception:
    # Something blew up - clean up what we can and get out of dodge
    traceback.print_exc(file=sys.stdout)
    os.system("pkill omxplayer")
    os.system("sudo pkill fbi")
  sys.exit(0)


if __name__ == "__main__":
    main()
