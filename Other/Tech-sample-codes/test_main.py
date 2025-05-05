#!/usr/bin/env python
#-*- coding:UTF-8 -*-

import os, time, sys
#import keyboard  #don't use

# for global keyboard control
from pynput import keyboard
from pynput.keyboard import Key, Listener, Controller

# for browser/window control
import selenium
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

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
# read token from file
token = None
if os.path.isfile('./token.txt'):
  try:
    with open('./token.txt', "r") as f:
      for line in f:
        token = line.strip()
        print('read token: (',token,')',sep='')
        break
  except Exception as e:
    print(e)
else:
  print('token file ./token.txt not found')

if token is None:
  os._exit(1)


# 設定 geckodriver 路徑
#if os.name == 'nt':
#  service = Service(executable_path='C:/selenium/geckodriver.exe')
if os.path.isfile('./geckodriver'):
  service = Service(executable_path='./geckodriver')
if os.path.isfile('/root/geckodriver'):
  service = Service(executable_path='/root/geckodriver')
elif os.path.isfile('/snap/bin/firefox.geckodriver'):
  service = Service(executable_path='/snap/bin/firefox.geckodriver')
else:
  print('Driver for firefox not found!')
  os._exit(1)

# use EWMH module
ewmh = EWMH()

# kill existent firefox
os.system('pkill firefox')
# 以下僅供參考
# Or use below to do the same thing
#wins = ewmh.getClientList()
#for w in wins:
#  wm_class = w.get_wm_class()
#  if wm_class[0] == 'Navigator' and wm_class[1] == 'firefox':
#    print('Kill found firefox, XWIN=%x, title="%s"' % (w.id, ewmh.getWmName(w).decode('utf-8')))
#    os.kill(ewmh.getWmPid(w), signal.SIGTERM)

home_url = 'https://demo.n1s168.com/#/'

# 啟動選項（這裡你也可以加入 --kiosk）
options = Options()
#options.add_argument('-kiosk')  # 無邊框、全螢幕模式
options.add_argument('-private-window')
#options.add_argument('--window-position=0,0')
#options.add_argument('--width=768')   # 根據你螢幕調整
#options.add_argument('--height=1366')

# 啟動瀏覽器 (將產生一內定分頁 BLANK as dummy page)
driver = webdriver.Firefox(service=service, options=options)

# 開啟遊戲分頁.
game_tab_handle = driver.current_window_handle
driver.get(home_url + token)
# 以下加入 javascript 來攔截事件. 但經過實驗, 一旦 reload 後就會失效.
# 避免 right click 叫出 contentmenu
driver.execute_script('document.addEventListener("contextmenu", function(e) {e.preventDefault();});')
# 避免按下若干種按鍵. 
driver.execute_script('document.addEventListener("keydown", e => {if(e.key=="F3"||e.key=="F6"||e.key=="F7"||e.key=="F10"||e.key=="F11"||e.key=="F12"){e.preventDefault();}});')

# 開啟 Setting 分頁(先使用 CUPS setting 來假裝).
driver.switch_to.new_window('tab')
setting_tab_handle = driver.current_window_handle
driver.get('https://127.0.0.1:631')
# 避免 right click 叫出 contentmenu
driver.execute_script('document.addEventListener("contextmenu", function(e) {e.preventDefault();});')

# let game page active
driver.switch_to.window(game_tab_handle)
web_wait_obj = WebDriverWait(driver, 10)

assert len(driver.window_handles) == 2

#以下命令調整視窗比例
# For firefox only
# 以下方式有問題, 因為是整個視窗內容直接放大, 元件不會自適應.
#driver.execute_script('document.body.style.MozTransform = "scale(1.50)";')
#要求要模擬按下 Ctrl-+ 來 Zoom In. 使元件自適應.
'''
# 以下方法可行, 但最後決定使用 Selenium 的.
kb_con = Controller()
kb_con.press(Key.ctrl)
time.sleep(0.2)
for _ in range(5):
  kb_con.tap('=')
  time.sleep(0.1)
kb_con.release(Key.ctrl)
'''

#time.sleep(0.2)
driver.set_context("chrome")
win = driver.find_element(By.TAG_NAME,"html")
for _ in range(5):
    win.send_keys(Keys.CONTROL + "=")
driver.set_context("content")

# create selenium action object
actions = ActionChains(driver)

'''
以下方式不行.
ActionChains(driver).\
    find_element_by_tag_name('window').\
    key_down(Keys.CONTROL).\
    pause(0.2).\
    send_keys("=").\
    pause(0.2).\
    send_keys("=").\
    pause(0.2).\
    send_keys("=").\
    pause(0.2).\
    send_keys("=").\
    pause(0.2).\
    send_keys("=").\
    key_up(Keys.CONTROL).\
    perform()
'''

# 這些 handle 的內容都是 uuid
print('game page:', game_tab_handle)
print('setting page:', setting_tab_handle)

'''
# 以下僅供參考

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
  print('Firefox browser not foune! Logic error!')
  driver.quit()
  os._exit(1)

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
  os._exit(1)
'''

#########################################################
# Handle global keyboard/key events
#########################################################

def find_css_element(name:str, timeout_sec = 0.0):
    ele = None
    ts = time.time()    # 取得 timestamp (float)(second)
    try:
        if timeout_sec < 0.0000001
            ele = driver.find_element(By.CSS_SELECTOR, name)
        else
            ele = WebDriverWait(driver, timeout_sec).until(EC.element_to_be_clickable((By.CSS_SELECTOR, name)))

    except selenium.common.exceptions.TimeoutException:         # 超過設定時間依然未載入完成.
        pass
    except selenium.common.exceptions.NoSuchElementException:   # 在載入完成的情況下找不到該元素.
        pass
    except selenium.common.exceptions.WebDriverException as e:
        print('web driver except:', e)
    except Exception as e:
        print('except:', e)

    print('take',time.time() - ts,'sec to click')
    return ele

def on_button(func: str):
  print('button', func, 'pressed')

  if func == 'spin':
    if not driver.current_url.startswith(home_url):
        actions.send_keys(' ').perform()
        #kb_con.tap(' ')

  elif func == 'cashout':
    pass

  elif func == 'home':
    # Just switch to 'Home' tab.
    # If it's not in home page or in game, always do auto-login
    if not driver.current_url.startswith(home_url):
        print('Reload HOME page')
        driver.switch_to.window(game_tab_handle)
        driver.get(home_url + token)

  elif func == 'vol+':
    os.system('amixer set Master 5%+ | grep "^  Mono:"')
    pass

  elif func == 'vol-':
    os.system('amixer set Master 5%- | grep "^  Mono:"')
    pass

  elif func == 'refresh':
    if driver.current_url.startswith(home_url):
        while True:
            ts = time.time()    # 取得 timestamp (float)(second)
            # 首先, 直接找尋 refresh 物件:
            refresh_icon = find_css_element('i.mdi-refresh.mdi.v-icon')
            if refresh_icon is not None:
                break

            # 如果沒找到, 改找尋 login 物件, 如果有, 表示要求自動登入.
            login_button = find_css_element("button.text-white.pr-\\[20px\\].cursor-pointer")
            if login_button is not None:
                break
            
            # 如果都沒有, 則等待一下, 並再找一次.
            refresh_icon = find_css_element('i.mdi-refresh.mdi.v-icon.notranslate', 5)
            break

        if refresh_icon is not None:
            refresh_icon.click()
        else:
            # reload the whole page
            driver.get(home_url + token)

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
