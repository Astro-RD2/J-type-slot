#!/usr/bin/env python
#-*- coding:UTF-8 -*-

import os, time, sys
import threading, queue

# for global keyboard control
from pynput import keyboard
from pynput.keyboard import Key, Listener, Controller

import serial

class ICT_ReceiptPrinter(threading.Thread):
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
    self.status = 0x8000
    pass
  
  def stop(self):
     b_stop = True
  
  # call start() to start run()
  def run(self):
    while not self.b_stop:
      # phase 1: if not opened, open it
      if not self.b_opened:
        try 
          handle = serial.Serial(self.dev, self.baurate, 8, 'N', 1, xonxoff=True,
              timeout=self.read_timeout, inter_byte_timeout=self.inter_byte_timeout, write_timeout=self.write_timeout)
          if handle.is_open:
            self.b_opened = True
            self.b_ready = False
        except ValueError as e:
          print('value except:', e)
        except serial.serialutil.SerialException as e:   # FileNotFoundError
          print('serial except:', e)
        except Exception as e:
          print('except:', e)
        
        if not self.b_opened:
          time.sleep(2)
          continue

        # restore to factory default: 無底線、取消反白、單倍寬、單倍高、16x24 字型、ASCII 編碼模式、字元靠左對齊、一維條碼位置重置、一維條碼高 140 點: 1B 40
        # (no response)
        handle.write(b'\x1b\x40')
        time.sleep(0.5)

      if not self.b_ready:
        try
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
            print('status:', ret)
            self.status = int.from_bytes(ret, "little")
            self.b_ready = True
        except serial.serialutil.SerialException as e:      # OSError
          print('serial except:', e)
          self.b_opened = False
        except Exception as e:
          print('except:', e)
          self.b_opened = False

        if not self.b_opened:
          try
            handle.close()
          except:
            pass
        time.sleep(0.5)

      if self.b_ready
        # phase 2: if there is task, do it; else check status regularily.
        task = None
        try
          task = task_q.get(timeout = 1.0)
        except queue.Empty:
          pass  # no data in queue
        except Exception as e:
          print('except:', e)
          
        # if there is task, ...
        if task is not None:
          # output to receipt printer
            
        # if no task, read status
        else:
     

  # push page task to queue 
  # return > 0: success and the value tells how many jobs in task queue
  # return -1: no link or current is not in state of able to print
  # return -2: failure, queue mechanism error (queue full or was shut down, this is logic error)
  def print_page(self, page_data: str): int
    if not self.b_ready:
      return -1

    try
      if self.task_q.full():
        return -2     # output queue full
      self.task_q.put(page_data, timeout = 0.1)
    except Exception as e:
      print('except:', e)
      return -2
    # trigger event
    #self.event.set()
  
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
  #   bit11~bit14 (reserved)
  #   bit15=1 lost link (no port or cable disconnected) ->fail to switch to ESC/POS or cannot read status
  def get_status(self): int
    if self.b_ready:
      return self.status | 0x8000
    return self.status

  

# for browser/window control
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By

# for browser/window states monitoring
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Use to get process Id, Window Id for low-level control.
from Xlib import XK, display, ext, X, protocol
from ewmh import EWMH

#########################################################
# Initialize the browser with two TAB's opened.
#
# Tab#1: the game page;    URL: https://demo.n1s168.com/#/<token>
# Tab#1: the setting page; URL: https://127.0.0.1:631    暫定.
#########################################################

# 設定 geckodriver 路徑
#if os.name == 'nt':
#  service = Service(executable_path='C:/selenium/geckodriver.exe')
if os.path.isfile('./geckodriver'):
  service = Service(executable_path='./geckodriver')
elif os.path.isfile('/snap/bin/firefox.geckodriver'):
  service = Service(executable_path='/snap/bin/firefox.geckodriver')
else:
  printf('Driver for firefox not found!')
  sys._exit(1)

# use EWMH module
ewmh = EWMH()

# kill existent firefox
os.system('pkill firefox')
# Or use below to do the same thing
#wins = ewmh.getClientList()
#for w in wins:
#  wm_class = w.get_wm_class()
#  if wm_class[0] == 'Navigator' and wm_class[1] == 'firefox':
#    print('Kill found firefox, XWIN=%x, title="%s"' % (w.id, ewmh.getWmName(w).decode('utf-8')))
#    os.kill(ewmh.getWmPid(w), signal.SIGTERM)

# 啟動選項（這裡你也可以加入 --kiosk）
options = Options()
#options.add_argument('-kiosk')  # 無邊框、全螢幕模式
options.add_argument('-private-window')
#options.add_argument('--window-position=0,0')
#options.add_argument('--width=768')   # 根據你螢幕調整
#options.add_argument('--height=1366')

# 啟動瀏覽器 (將產生一內定分頁 BLANK as dummy page)
driver = webdriver.Firefox(service=service, options=options)
dummy_tab_handle = driver.current_window_handle

# 開啟遊戲分頁.
driver.switch_to.new_window('tab')
game_tab_handle = driver.current_window_handle
driver.get('https://demo.n1s168.com/#/eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiY2MwMTdiZWQ4N2M4ODA4ZTVjMDIwMmNiYjJiZDViNzRjZGI4MjRjY2Y4MDgxZTgxYjMyMDNmMWZlYWExOTQyMTM4OWM0OWFmMmE5ZTI0NjgiLCJpYXQiOjE3NDU1NzM4MjQuODc0OTc5LCJuYmYiOjE3NDU1NzM4MjQuODc0OTgzLCJleHAiOjE3NzcxMDk4MjQuODYwMDYxLCJzdWIiOiIzMDAzOCIsInNjb3BlcyI6W119.xyl-PVabt8yJzW2ppC_VQyfAb5-KEsDJsnFjHME0TTk_rW4mmeJz796Zxs6CGwSgFc75oGYjSrGVloUvQ1mjh3xUrjpjg2G9jvMpdrGaobquXH9si7s971-8wGCrsbSLybB4JFJKtQHh5OY9CdM7HIVqTn3ukQ8YTDN-0Q8eHDZpPkOZo7rERHJHNOcgmgw1HVOxR8XuGhmWB7bxD7Be6fr2U3q1jOFaP_90u3ZVlSHBj8jqcnKqPCQdcI8ZIdA39YswYfS86t9rITSTGnZTmIvuooxyoR16I44DfesJ9pUYQCB85my39koaXG3vdMCqqrcZaFzATC_2RPa57859RnYYIveqgTxr8tWAWON4Hdl4ci0QfP5CcoD6FkC0PsInZFj5pHm58jo3E92RCw4BuGO9JhQhcvxAsKaaGz2MOwzj7pZSmF-CQ5qH0apYEr9xr1qgGwAWVWkeWmhPvfUrTt2i29t-9qW2Wz05XFTtu8BORp760jSR1uujIDsEK7Y-feol7bxJsQdNEFzii2Em-BbqO5MqG5KGjnePMS6BcdQx2EYnfmcE_dKRQfoY2CvDsZXzcUoCijpPJqMWhTGxrl5MWEo2vos4szb79_TMAv4cHsztCigoq-KBVGiR4GBSkDDXKcK0Go1LRonFPgcTECDdVCwOPWEwSxbgWbuPxDk')
# 以下加入 javascript 來攔截事件. 但經過實驗, 一旦 reload 後就會失效/
# 避免 right click 叫出 contentmenu
driver.execute_script('document.addEventListener("contextmenu", function(e) {e.preventDefault();});')
# 避免按下若干按鍵. 
driver.execute_script('document.addEventListener("keydown", e => {if(e.key=="F3"||e.key=="F6"||e.key=="F7"||e.key=="F10"||e.key=="F11"||e.key=="F12"){e.preventDefault();}});')

# 開啟 Setting 分頁(先使用 CUPS setting 來假裝).
driver.switch_to.new_window('tab')
setting_tab_handle = driver.current_window_handle
driver.get('https://127.0.0.1:631')
# 避免 right click 叫出 contentmenu
driver.execute_script('document.addEventListener("contextmenu", function(e) {e.preventDefault();});')

driver.switch_to.window(dummy_tab_handle)
driver.close()
# let game page active
driver.switch_to.window(game_tab_handle)
WebDriverWait(driver, 10)

assert len(driver.window_handles) == 2

#以下命令調整視窗比例
# For firefox only
# 以下方式有問題, 因為是整個視窗內容直接放大, 元件不會自適應.
#driver.execute_script('document.body.style.MozTransform = "scale(1.50)";')
#要求要模擬按下 Ctrl-+ 來 Zoom In. 使元件自適應.
kb_con = Controller()
kb_con.press(Key.ctrl)
time.sleep(0.2)
for _ in range(5):
  kb_con.tap('=')
  time.sleep(0.2)
kb_con.release(Key.ctrl)

# 這些 handle 的內容都是 uuid
print('game page:', game_tab_handle)
print('setting page:', setting_tab_handle)

# Confirm whether existing new-launched process
# 取得新開之 Firefox 的 Process ID 以及其主視窗的 Window ID  (後著考慮作為之後 XEvent keyboard 的標的)
wins = ewmh.getClientList()
browser_win = -1
browser_pid = -1
for w in wins:
  wm_class = w.get_wm_class()
  # 以下是找到 Firefox window 的識別方式. (經過觀察 與 wmctrl 應用程式來找到的)
  if wm_class[0] == 'Navigator' and wm_class[1] == 'firefox':
    browser_win = w
    browser_pid = ewmh.getWmPid(w)
    break

# if not being launched, this is logic error!
if browser_win == -1:
  printf('Firefox browser not foune! Logic error!')
  driver.quit()
  sys._exit(1)

print('Firefox title:', ewmh.getWmName(browser_win).decode('utf-8'))    # get title
print('Firefox process ID:', browser_pid)
print()

# 另外一種方式取得 browser 的 Process ID, 但無法取得 Window ID
my_dict = driver.capabilities
print("PID of the browser process is:", my_dict['moz:processID'])
# for debug, and see what properties are in driver.capabilities
print(my_dict)
if browser_pid != my_dict['moz:processID']:
  print('Process ID is differnet values from Selenium driver and XLib')
  driver.quit()
  sys._exit(1)


#########################################################
# Handle global keyboard/key events
#########################################################

def on_button(func: str):
  print('button', func, 'pressed')

  if func == 'spin':
    pass
  elif func == 'cashout':
    pass
  elif func == 'home':
      driver.switch_to.window(game_tab_handle)
      print('URL:', driver.current_url)
      if not driver.current_url.startswith('https://demo.n1s168.com/#/'):
        print('Reload HOME page')
        driver.get('https://demo.n1s168.com/#/')
  elif func == 'vol+':
    pass
  elif func == 'vol-':
    pass
  elif func == 'refresh':
    pass
  elif func == 'operator':
      driver.switch_to.window(setting_tab_handle)
      print('URL:', driver.current_url)
      if not driver.current_url.startswith('https://127.0.0.1:631'):
        print('Reload SETTING page')
        driver.get('https://127.0.0.1:631')
    
loop = True
def req_quit():
  global loop
  print('ESC to quit')
  loop = False
  return False      # tell to stop the listen thread
  
listener = keyboard.GlobalHotKeys({
    '<ctrl>+<alt>+<enter>': lambda: on_button('spin'),
    '<ctrl>+<alt>+p': lambda: on_button('cashout'),
    '<ctrl>+<alt>+<home>': lambda: on_button('home'),
    '<ctrl>+<alt>+=': lambda: on_button('vol+'),
    '<ctrl>+<alt>+-': lambda: on_button('vol-'),
    '<ctrl>+<alt>+r': lambda: on_button('refresh'),
    '<ctrl>+<alt>+o': lambda: on_button('operator'),
    '<esc>': req_quit}) 
    # Note, cannot add parameter "suppress=True", which will block all keyboard and mouse events.
listener.start()

print("控制說明：Ctrl-Alt-Home=至遊戲分頁\nCtrl-Alt-O=至 Operator 分頁\nESC=關閉 Firefox")

#########################################################
# Main Loop
#########################################################

loop = True
while loop:
  # (tasks in main loop here)
  time.sleep(0.3)
    
driver.quit()

#except KeyboardInterrupt:
#    driver.quit()
#    print("手動中斷，結束程式。")
