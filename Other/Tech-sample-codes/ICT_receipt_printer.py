#!/usr/bin/env python
#-*- coding:UTF-8 -*-

import os, time, sys
import threading, queue

import keyboard
import serial

class ICT_SP1_ReceiptPrinter(threading.Thread):
  def __init__(self, dev: str, read_timeout=0.5, inter_byte_timeout=0.1, write_timeout=1.0, baudrate = 115200):
    threading.Thread.__init__(self)
    self.dev = dev
    self.baurate = baudrate
    self.read_timeout = read_timeout
    self.inter_byte_timeout = inter_byte_timeout
    self.write_timeout = write_timeout
    
    self.task_q = queue.Queue(16)
    self.b_stop = False     # stop this thread
    #self.event = threading.Event()
    #self.io_lock = threading.Lock()

    self.b_opened = False       # True if open('/dev/ttyACM0', ...) success
    self.b_ready = False        # True if completing all of reset => set the ESC/POS => get the first status
    self.status = 0xC000        # bit14=1 and bit13=1: no link and not ready
  
  def stop(self):
    self.b_stop = True
  
  # call start() to start run()
  def run(self):
    handle = None
    while not self.b_stop:
      # phase 1: if not opened, open it
      if not self.b_opened:
        print('reconnectng to printer ...')
        try:
          handle = serial.Serial(self.dev, self.baurate, 8, 'N', 1, xonxoff=True,
              timeout=self.read_timeout, inter_byte_timeout=self.inter_byte_timeout, write_timeout=self.write_timeout)
          if handle.is_open:
            # restore to factory default: 無底線、取消反白、單倍寬、單倍高、16x24 字型、ASCII 編碼模式、字元靠左對齊、一維條碼位置重置、一維條碼高 140 點: 1B 40
            # (no response)
            handle.write(b'\x1b\x40')
            handle.flush()
            time.sleep(0.5)
            self.b_opened = True
            self.b_ready = False
            self.sttus = 0x4000     # bit13=1: not ready
        except ValueError as e:
          print('value range except:', e)
        except serial.serialutil.SerialException as e:   # FileNotFoundError
          print('serial except:', e)
        except Exception as e:
          print('except:', e)

      elif not self.b_ready:
        print('initializing printer ...')
        try:
          # Reset printer  (Just reset inner task, no setting changed)
          # (no response)
          handle.write(b'\x1b\x72\x00')

          # Switch to ESC/POS protocol
          # return \x1b\x23 (ESC #) if success
          handle.write(b'\x1b\x23')
          handle.flush()
          ret = handle.read(64)
          print('protocol:', ret)
          if ret == b'\x1b\x23':
            # read printer status
            handle.write(b'\x1d\x61')
            handle.flush()
            ret = handle.read(64)
            self.status = int.from_bytes(ret, "little") & 0x7ff
            #print('status: ' + hex(ret))
            self.b_ready = True
            time.sleep(0.5)
        except serial.serialutil.SerialException as e:      # OSError
          print('serial except:', e)
          self.b_opened = False
        except Exception as e:
          print('except:', e)
          self.b_opened = False

      else:
        # phase 2: if there is task, do it; else check status regularily.
        task = None
        try:
          task = self.task_q.get(timeout = 1.0)
        except queue.Empty:
          pass  # no data in queue
        except Exception as e:
          print('except:', e)

        try:
          # if there is task, ...
          if task is not None:
            print('got a task', task)
            # output to receipt printer
            pass
            
          # if no task, read status
          else:
            # read printer status
            handle.write(b'\x1d\x61')
            handle.flush()
            ret = handle.read(64)
            self.status = int.from_bytes(ret, "little") & 0x7ff
            #print('status: ' + hex(ret))
        except serial.serialutil.SerialException as e:   # FileNotFoundError
          print('serial except:', e)
          self.b_opened = False
        except Exception as e:
          print('except:', e)
          self.b_opened = False

      if not self.b_opened:
        self.b_ready = False
        self.status = 0xC000
        if handle is not None:
          try:
            handle.close()
          except:
            pass
          handle = None
        time.sleep(1)


  # push page task to queue 
  # return > 0: success and the value tells how many jobs in task queue
  # return -1: no link or current is not in state of able to print
  # return -2: failure, queue mechanism error (queue full or was shut down, this is logic error)
  def print_page(self, page_data: str) -> int:
    if self.status != 0:
      return -1

    try:
      if self.task_q.full():
        return -2     # output queue full
      self.task_q.put(page_data, timeout = 0.1)
    except Exception as e:
      print('except:', e)
      return -2
    
    return self.task_q.qsize()
  
  # return: int
  #   --- low byte below
  #   bit0=1 cover open or no paper on thermal head
  #   bit1=1 roller paper empty
  #   bit2=1 cutter malfunction
  #   bit3=1 anti-pulling sensor masked  (只適用於有防拉機型)
  #   bit4=1 check-sum error
  #   bit5=1 no SD card ready
  #   bit6=1 abnormal temperature
  #   bit7=1 SD file error
  #   --- high byte below
  #   bit8=1 roller paper low level warning
  #   bit9=1 out paper sensor mask  (for model NNX only)
  #   bit10=1 paper jam
  #   bit11~bit13 (reserved)
  #   bit14=1 printer not initialized yet
  #   bit15=1 lost link (no port or cable disconnected) ->fail to switch to ESC/POS or cannot read status
  # Remark:
  #   bit0~bit10 are valid only if bit14=0
  def get_status(self) -> int:
    return self.status


if __name__ == '__main__':
  b_quit = False
  print_id = 0
  def esc_quit_print():
    global b_quit
    print('[esc] request to quit')
    b_quit = True

  def print_sample_page():
    global print_id
    print_id += 1
    print('[p] request to print, task', print_id)
    ret = prn.print_page(str(print_id))
    if ret < 0:
      print('fail to print, ignored')
    else:
      print('to print queue (%d data queued)' % ret)

  prn = ICT_SP1_ReceiptPrinter('/dev/ttyACM0')
  try:
    prn.start()
  except:
    print('cannot launch printer object')
    sys._exit(1)

  keyboard.add_hotkey('esc', esc_quit_print)
  keyboard.add_hotkey('p', print_sample_page)
  
  while not b_quit:
    print('status: ' + hex(prn.get_status()))
    time.sleep(1)
      
  prn.stop()
  try:
    prn.join()
  except:
    pass


