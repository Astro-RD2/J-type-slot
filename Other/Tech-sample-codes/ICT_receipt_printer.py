#!/usr/bin/env python
#-*- coding:UTF-8 -*-

import os, time, sys
import threading, queue

import keyboard
import serial

class ICT_SP1_ReceiptPrinter(threading.Thread):
    def __init__(self, dev: str, read_timeout=0.5, inter_byte_timeout_sec=0.1, write_timeout_sec=1.0, baudrate = 115200):
        threading.Thread.__init__(self)
        self.dev = dev
        self.baurate = baudrate
        self.read_timeout = read_timeout
        self.inter_byte_timeout_sec = inter_byte_timeout_sec
        self.write_timeout_sec = write_timeout_sec
        
        self.task_q = queue.Queue(16)
        self.b_stop = False     # stop this thread
        #self.event = threading.Event()
      
        self.b_opened = False       # True if open('/dev/ttyACM0', ...) success
        self.b_ready = False        # True if completing all of reset => set the ESC/POS => get the first status
        
        self.status_lock = threading.Lock()
        self.status = 0b1100000000000000    # bit15=1 and bit14=1: no link and not ready
        
        self.fail_count:int = 0     # accumulate how many failures in a row
    
    # clear all tasks in waiting queue
    def clear(self):
        self.status_lock.acquire()
        while not self.task_q.empty():
            self.status_lock.release()
            try:
                self.task_q.get_no_wait()
            except:
                pass
            self.status_lock.acquire()
        self.status &= 0b1101111111111111
        self.status_lock.release()
        self.fail_count = 0

    def stop(self):
        self.b_stop = True
    
    # call start() to start run()
    def run(self):
      handle = None
      task = None
      task_state = 0
      while not self.b_stop:
        # phase 1: if not opened, open it
        if not self.b_opened:
            print('reconnectng to printer ...')
            try:
                handle = serial.Serial(self.dev, self.baurate, 8, 'N', 1, xonxoff=True,
                    timeout=self.read_timeout, inter_byte_timeout=self.inter_byte_timeout_sec, 
                    write_timeout=self.write_timeout_sec)
                if handle.is_open:
                    # restore to factory default: 
                    # 無底線、取消反白、單倍寬、單倍高、16x24 字型、ASCII 編碼模式、字元靠左對齊、一維條碼位置重置、一維條碼高 140 點: 1B 40
                    # (no response)
                    handle.write(b'\x1b\x40')
                    handle.flush()
                    time.sleep(0.5)
                    self.b_opened = True
                    self.b_ready = False
                    self.status_lock.acquire()
                    # bit14=1: not ready, bit13=1: waiting task available
                    self.status = 0b0100000000000000 | (self.status & 0b0010000000000000)
                    self.status_lock.release()
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
                print('protocol:', 'ICT-ESC/POS' if ret == b'\x1b\x23' else ('Unknown ' + ret))
                if ret == b'\x1b\x23':
                    # read printer status
                    handle.write(b'\x1d\x61')
                    handle.flush()
                    ret = handle.read(64)
                    ret_len = len(ret)
                    #print('status: ' + hex(ret))
                    if ret_len != 2:
                        print('illegal return len:', ret_len)
                        if ret_len == 0:
                            print('read timeout')
                        else:
                            ret_hex = '0x' + ''.join(['%02X' % b for b in ret])
                            print('illegal return:', ret_hex)
                        self.b_opened = False
                    else:
                        status = int.from_bytes(ret, "little") & 0x7ff
                        self.status_lock.acquire()
                        self.status = status | (self.status & 0b0010000000000000)
                        self.status_lock.release()
                        self.fail_count = 0
                        task_state = 0
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
            if task is None:
                try:
                    #ts = time.time()
                    task = self.task_q.get(timeout = 1.0)   # (second)
                    if task is not None:
                        print('got a printing task')
                        task_state = 0
                    #print('got task. wait',time.time() - ts,'sec')
                except queue.Empty:
                    #print('queue empty. wait',time.time() - ts,'sec')
                    # may be empty, but need to confirm
                    self.status_lock.acquire()
                    if self.task_q.empty():
                        self.status &= 0b1101111111111111
                    self.status_lock.release()
                except Exception as e:
                    print('except:', e)
          
            try:
                # if there is task, ...
                if task is not None:
                    # task_state==0, do output
                    if task_state == 0:
                        #print('got a printing task', task)
                        # output to receipt printer
                        handle.write(task.encode('ascii'))
                        handle.flush()
                        handle.write(b'\x0c')
                        handle.flush()
                        task_state = 1
                        task_state_ts = time.time() # get the time stamp
                        time.sleep(1)
                    elif time.time() - task_state_ts > 5.0:
                        # printing timeout  (no receive the page ended for 5 seconds
                        print('wait for page printed out totally but timeout')
                        self.b_opened = False
                    else:
                        # wait for b'\x0c' to indicate the printing is over
                        ret = handle.read(64)       # receive any returned data
                        if ret != b'':
                            print('wait for page-end, got', ret)
                            b_found_page_end = False
                            for b in ret:
                                if b == ord(b'\x0c'):
                                    b_found_page_end = True
                                    print('page end signal')
                                    break
                            if b_found_page_end:
                                self.fail_count = 0
                                task = None
                  
                # if no task, read status
                # 讀取狀態. 連續三次 timeout, 視為斷線.
                else:
                    # read printer status
                    handle.read(64)     # read out garbage
                    handle.write(b'\x1d\x61')
                    handle.flush()
                    ret = handle.read(64)
                    #print('status: ' + hex(ret))
                    ret_len = len(ret)
                    if ret_len != 2:
                        print('illegal return len:', ret_len)
                        if ret_len == 0:
                            self.fail_count += 1
                            print('read timeout (cont. ', self.fail_count, ')', sep='')
                            if self.fail_count == 3:
                                print('regard as disconnect')
                                self.fail_count = 0
                                self.b_opened = False
                        else:
                            ret_hex = '0x' + ''.join(['%02X' % b for b in ret])
                            print('illegal return:', ret_hex)
                            self.b_opened = False
                    else:
                        status = int.from_bytes(ret, "little") & 0x7ff
                        self.status_lock.acquire()
                        self.status = status | (self.status & 0b0010000000000000)
                        self.status_lock.release()
                        self.fail_count = 0
                    
            except serial.SerialTimeoutException as e:
                print('serial write except:', e)
                self.b_opened = False
            except serial.serialutil.SerialException as e:   # FileNotFoundError
                print('serial except:', e)
                self.b_opened = False
            except Exception as e:
                print('except1:', e)
                self.b_opened = False
   
        if not self.b_opened:
            self.b_ready = False
            self.status_lock.acquire()
            self.status = 0b1100000000000000 | (self.status & 0b0010000000000000)
            self.status_lock.release()
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
        status = self.get_status()
        if status & 0b1101111111111111 != 0:
            return -1
      
        try:
            if self.task_q.full():
                return -2     # output queue full
            self.task_q.put(page_data, timeout = 0.1)
            self.status_lock.acquire()
            if not self.task_q.empty():
                self.status |= 0b0010000000000000
            self.status_lock.release()
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
    #   --
    #   bit4=1 check-sum error
    #   bit5=1 no SD card ready
    #   bit6=1 abnormal temperature
    #   bit7=1 SD file error
    #   --- high byte below
    #   bit8=1 roller paper low level warning
    #   bit9=1 out paper sensor mask  (for model NNX only)
    #   bit10=1 paper jam
    #   bit11   (reserved to 0)
    #   --
    #   bit12   (reserved to 0)
    #   bit13=1 waiting task available
    #   bit14=1 printer not initialized yet
    #   bit15=1 lost link (no port or cable disconnected) ->fail to switch to ESC/POS or cannot read status
    # Remark:
    #   bit0~bit10,bit14 are valid only if bit15=0
    def get_status(self) -> int:
        self.status_lock.acquire()
        status = self.status
        self.status_lock.release()
        return status

    def get_status_list(self) -> list:
        status = self.get_status()
        s = []
        if status & 0b1100000000000000 > 0:     # bit 15/14
            s += ['Disconnected']
        else:
            if status & 0b0000010111111111 > 0:
                if status & 0b0000010000000000 > 0:   # bit 10
                    s += ['Paper jam']
                if status & 0b0000000100000010 > 0:   # bit 8/1
                    s += ['Paper low or empty']
                if status & 0b0000000010000000 > 0:   # bit 7
                    s += ['SD file error']
                if status & 0b0000000001000000 > 0:   # bit 6
                    s += ['Abnormal temperature']
                if status & 0b0000000000100000 > 0:   # bit 5
                    s += ['No SD card ready']
                if status & 0b0000000000010000 > 0:   # bit 4
                    s += ['Check-sum error']
                if status & 0b0000000000001000 > 0:   # bit 3
                    s += ['Pulling detected']
                if status & 0b0000000000000100 > 0:   # bit 2
                    s += ['Pulling detected']
                if status & 0b0000000000000001 > 0:   # bit 0
                    s += ['Cover open or no paper on head']
        return s

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
        '''
        s = b'\x1c\x45Hello World\x1c\x46\n\n\n' +\
            #b'serial:' + str(print_id).encode('utf8') + b'\n\n' +\
            b'Amount: USD$1234.5\n\n' +\
            b'Terminal ID: 381292\n\n' +\
            b'TX ID: 123e4567-e89b-12d3-a456-426655440000\n'
        '''
        s = '\x1b\x4d\x03\x1c\x45Hello Casino\x1c\x46\x1b\x4d\x01\n\n' +\
            'Amount: USD$1234.5\n\n' +\
            'Serial:' + str(print_id) + '\n\n' +\
            'Terminal ID: 381292\n\n' +\
            'TX ID:\n123e4567-e89b-12d3-a456-426655440000\n'
        ret = prn.print_page(s)  # str(print_id))
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
    
    last_status = 0xffff
    while not b_quit:
        curr_status = prn.get_status()
        if curr_status != last_status:
            print('status: ' + hex(curr_status))
            last_status = curr_status
        time.sleep(1)
        
    prn.stop()
    try:
        prn.join()
    except:
        pass


