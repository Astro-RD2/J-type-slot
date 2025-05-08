#!/usr/bin/env python
#-*- coding:UTF-8 -*-

import os, time, datetime, sys
import subprocess, threading
#import keyboard  #don't use
import uinput

# for global keyboard control
from pynput import keyboard
from pynput.keyboard import Key, Listener, Controller
import configparser
from urllib.parse import urlparse

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
# (not use)
#from Xlib import XK, display, ext, X, protocol
#from ewmh import EWMH

from ICT_receipt_printer import ICT_SP1_ReceiptPrinter
from n1s168_webapi import n1s168_webapi


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
  print('use ./geckodriver')
  service = Service(executable_path='./geckodriver')
elif os.path.isfile('/root/geckodriver'):
  print('use /root/geckodriver')
  service = Service(executable_path='/root/geckodriver')
elif os.path.isfile('/snap/bin/firefox.geckodriver'):
  print('use /snap/bin/firefox.geckodriver')
  service = Service(executable_path='/snap/bin/firefox.geckodriver')
else:
  print('Driver for firefox not found!')
  os._exit(1)

#
# read global configuration
#
config = configparser.ConfigParser()

def load_config():
    try:
        if os.path.isfile('./setting.ini'):
            config.read('./setting.ini', encoding='utf8')
        elif os.path.isfile('/root/astro/data/setting.ini'):
            config.read('/root/astro/data/setting.ini', encoding='utf8')
        else:
            print('fail to read configuration')
            os._exit(1)
    except Exception as e:
        print('except:', e)

load_config()

#
# initial Web API interface
#
webapi = n1s168_webapi()
try:
    urls = config['BASIC']['HOME_URL']
    home_url = urls.split(',')[0]
    api_url = urls.split(',')[1]
    webapi.set_api_base_url(api_url);
    home_hostname = urlparse(home_url)[1]
    api_hostname = urlparse(api_url)[1]
except:
    print('failed to read config or bad format')
    os._exit(1)

home_url_with_slash = home_url
if home_url[-1] != '/':
    home_url_with_slash += '/'
print('Home url:', home_url)
print('Home url (with tailed /):', home_url_with_slash)

token = config['REGISTER']['TOKEN']
# if no token, acquire one
if token == '':
    for _ in range(30):
        print('fetch token....')
        json_data = webapi.fetch_token('ITgame01', 'ITgame01')
        if json_data['result_code'] == 0:
            print('0=success')
            token = json_data['token']
        elif json_data['result_code'] == -1:
            print('-1=API request error')
        elif json_data['result_code'] == -2:
            print('-2=http status code is not 2xx')
        elif json_data['result_code'] == -3:
            print('-3=status field is False')
        else:
            print('unknown', json_data['result_code'])

        if token != '':
            break
        time.sleep(5)

if token == '':
    print('cannot got token, quit')
    os._exit(1)

def kill_all_firefox():
    # kill all existent firefox proceses
    os.system('pkill firefox')
    
    # 以下僅供參考 (另外一種方式)
    # use EWMH module
    #ewmh = EWMH()

    #wins = ewmh.getClientList()
    #for w in wins:
    #  wm_class = w.get_wm_class()
    #  if wm_class[0] == 'Navigator' and wm_class[1] == 'firefox':
    #    print('Kill found firefox, XWIN=%x, title="%s"' % (w.id, ewmh.getWmName(w).decode('utf-8')))
    #    os.kill(ewmh.getWmPid(w), signal.SIGTERM)

kill_all_firefox()

# 啟動選項（這裡你也可以加入 --kiosk）
options = Options()
print('argument(s):', end='')
for i in range(1, len(sys.argv)):
    print('[%s]' % sys.argv[i], end='')
    # 無邊框、全螢幕模式
    if sys.argv[i] == '-kiosk' or sys.argv[i] == '--kiosk':
        options.add_argument('-kiosk')
print()

options.add_argument('-private-window')
options.add_argument('-remote-allow-system-access')     # 突然必須有此, 不了解理由. 加上就對了.
options.add_argument('--window-position=0,0')
options.add_argument('--width=1080')   # 根據你螢幕調整
options.add_argument('--height=1920')

# 啟動瀏覽器 (將產生一內定分頁 BLANK as dummy page)
driver = webdriver.Firefox(service=service, options=options)

# 開啟遊戲分頁.
game_tab_handle = driver.current_window_handle
driver.get(home_url_with_slash + token)
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
# now, the driver.current_url contains <token>

assert len(driver.window_handles) == 2

#以下命令調整視窗比例
# For firefox only
# 以下方式有問題, 因為是整個視窗內容直接放大, 元件不會自適應.
#driver.execute_script('document.body.style.MozTransform = "scale(1.50)";')
#要求要模擬按下 Ctrl-+ 來 Zoom In. 使元件自適應.

# 以下方法可行, 但最後決定使用 Selenium 的.
'''
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

uinput_dev = uinput.Device([uinput.KEY_SPACE])

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
# Payment devices
#########################################################
# Launch printer thread
printer = ICT_SP1_ReceiptPrinter(config['DEVICE']['BILL_ACCEPTOR_PORT'])
try:
    printer.start()
except Exception as e:
    print('printer thread except:', e)
    webapi.join_all()
    os._exit(1)

# Launch bill acceptor
#(todo)


#########################################################
# Utility functions
#########################################################

# timeout_msec: keep how many milliseconds stay the notify message (millisecond)
def notify(timeout_msec:int|None = None, icon:str='dialog-warning', title:str='test title', message:str='test message'):
    if timeout_msec is None:
        subprocess.run(['notify-send', '-i', icon, title, message], capture_output=True)
    else:
        subprocess.run(['notify-send', '-t', str(timeout_msec), '-i', icon, title, message], capture_output=True)    

def find_css_element(name:str, timeout_sec = 0.0):
    ele = None
    #ts = time.time()    # 取得 timestamp (float)(second)
    try:
        if timeout_sec < 0.0000001:
            ele = driver.find_element(By.CSS_SELECTOR, name)
        else:
            ele = WebDriverWait(driver, timeout_sec).until(EC.element_to_be_clickable((By.CSS_SELECTOR, name)))

    except selenium.common.exceptions.TimeoutException:         # 超過設定時間依然未載入完成.
        pass
    except selenium.common.exceptions.NoSuchElementException:   # 在載入完成的情況下找不到該元素.
        pass
    except selenium.common.exceptions.WebDriverException as e:
        print('web driver except:', e)
    except Exception as e:
        print('except:', e)

    #print('take',time.time() - ts,'sec to click')
    return ele

#########################################################
# Main subroutines
#########################################################

# Try to click the Refresh icon if it's at HOME currently
def click_refresh():
    if driver.current_url.startswith(home_url):
        # 首先, 直接找尋 refresh 物件:
        refresh_icon = find_css_element('i.mdi-refresh.mdi.v-icon')
        try:
            if refresh_icon is not None:
                refresh_icon.click()
            else:
                driver.get(home_url_with_slash + token)
                # 避免 right click 叫出 contentmenu 以及避免按下若干種按鍵. 
                driver.execute_script('document.addEventListener("contextmenu", function(e) {e.preventDefault();});')
                driver.execute_script('document.addEventListener("keydown", e => {if(e.key=="F3"||e.key=="F6"||e.key=="F7"||e.key=="F10"||e.key=="F11"||e.key=="F12"){e.preventDefault();}});')
        except Exception as e:
            print('click_refresh except:', e)
                
    '''
    # for reference
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
            driver.get(home_url_with_slash + token)
            # 避免 right click 叫出 contentmenu 以及避免按下若干種按鍵. 
            driver.execute_script('document.addEventListener("contextmenu", function(e) {e.preventDefault();});')
            driver.execute_script('document.addEventListener("keydown", e => {if(e.key=="F3"||e.key=="F6"||e.key=="F7"||e.key=="F10"||e.key=="F11"||e.key=="F12"){e.preventDefault();}});')
    '''

cash_in_lock = threading.Lock()
cash_out_lock = threading.Lock()
cash_in_thr_ = None
cash_out_thr_ = None

# (todo): use thread instead for keyboard friendly
def cash_in(value:float = 10.0):
    print("enter cash_in()")
    if cash_in_lock.locked():
        print("cash_in() in progress, return")
        return

    cash_in_lock.acquire()
    try:
        ret = webapi.req_cashin(value);
        print('req_cashin() return ', end='')
        if ret == 0:
            print('0=success launched request')
        elif ret == -1:
            print('-1=API token lost or not given')
        elif ret == -2:
            print('-2=existing cashin phase 1 transaction')
        elif ret == -3:
            print('-3=existing cashin phase 2 transaction')
        elif ret == -9:
            print('-9=inner error or value is zero/negative')
        else:
            print('unknown', ret)
        
        if ret == 0:
            while True:
                json_data = webapi.wait_req_cashin_result(timeout_sec=0.1)
                if json_data['result_code'] != 1:
                    break
                #print(".")
            print(json_data)    # for debug
            print('wait_req_cashin_result() return ', end='')
            if json_data['result_code'] == 0:
                print('0=got result (http status ', json_data['http_status_code'],')(status ',json_data['status'],')',sep='')
            elif json_data['result_code'] == -1:
                print('-1=API request error')
            elif json_data['result_code'] == -2:
                print('-2=http status code is not 2xx (http status', json_data['http_status_code'],')')
            elif json_data['result_code'] == -3:
                print('-3=no prior request')
            elif json_data['result_code'] == -4:
                print('-4=disorder error')
            else:
                print('unknown', json_data['result_code'])

            if json_data["result_code"] != 0 or json_data["status"][0] != '0':
                print('Cash in transaction interrupted.')
                return
        
            print('Go to cash in phase 2')
            print('Stacking the banknote', value, 'dollars')
            time.sleep(3)
            ret = webapi.end_cashin()
            print('end_cashin() return ', end='')
            if ret == 0:
                print('0=success launched request')
            elif ret == -1:
                print('-1=API token lost or not given')
            elif ret == -2:
                print('-2=existing cashin phase 1 transaction')
            elif ret == -3:
                print('-3=existing cashin phase 2 transaction')
            elif ret == -4:
                print('-4=phase 1 not complete')
            elif ret == -9:
                print('-9=inner error')
            else:
                print('unknown', ret)

            if ret == 0:
                while True:
                    json_data = webapi.wait_end_cashin_result(timeout_sec=0.1)
                    if json_data['result_code'] != 1:
                        break
                    #print(".")
                print(json_data)    # for debug
                print('wait_end_cashin_result() return ', end='')
                if json_data['result_code'] == 0:
                    print('0=got result (http status ', json_data['http_status_code'],')(status ',json_data['status'],')',sep='')
                elif json_data['result_code'] == -3:
                    print('-3=no prior request')
                elif json_data['result_code'] == -4:
                    print('-4=disorder error')
                else:
                    print('unknown', json_data['result_code'])

            print('Cash in transaction ended.')
            click_refresh()
            notify(4000, 'face-smile-big', title='Welcome', message='%.2f dollars accepted' % json_data['value'])

    except Exception as e:
        print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        print('cash_in() except:', e)
        print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    finally:
        cash_in_lock.release()

def cash_out():
    if cash_out_lock.locked():
        return
    cash_out_lock.acquire()
    try:
        ret = webapi.req_cashout()
        print('req_cashout() return ', end='')
        if ret == 0:
            print('0=success launched request')
        elif ret == -1:
            print('-1=API token lost or not given')
        elif ret == -2:
            print('-2=existing cashout phase 1 transaction')
        elif ret == -3:
            print('-3=existing cashout phase 2 transaction')
        elif ret == -9:
            print('-9=inner error')
        else:
            print('unknown', ret)

        if ret == 0:
            while True:
                json_data = webapi.wait_req_cashout_result(timeout_sec=0.2)
                if json_data['result_code'] != 1:
                    break
                #print(".")
            print(json_data)    # for debug
            if json_data['result_code'] == 0:
                print('0=got result (http status ', json_data['http_status_code'],')(status ',json_data['status'],')',sep='')
            elif json_data['result_code'] == -1:
                print('-1=API request error')
            elif json_data['result_code'] == -2:
                print('-2=http status code is not 2xx (http status', json_data['http_status_code'],')')
            elif json_data['result_code'] == -3:
                print('-3=no prior request')
            elif json_data['result_code'] == -4:
                print('-4=disorder error')
            else:
                print('unknown', json_data['result_code'])
                return

            # if cannot go further, end
            if json_data["result_code"] != 0 or json_data["status"][0] != '0':
                print('Cash out transaction interrupted.')
                return
            
            print('Go to cash out phase 2')
            print('Printing the receipt with', json_data['value'], 'dollars')
            
            ret = printer.print_page(
                '\x1b\x4d\x03\x1c\x45' + config['BASIC']['TITLE'] + '\x1c\x46\x1b\x4d\x01\n\n' +\
                'Terminal ID: ITgame01\n\n' +\
                ('AMOUNT USD$%.2f\n\n' % json_data['value']) +\
                datetime.datetime.now().strftime('%c') + '\n\n' +\
                'TX ID:\n' + json_data['TXID'] + '\n')
            if ret < 0:
                print('fail to print (%d)' % ret)
                print('Cash out transaction interrupted.')

            ret = webapi.end_cashout()
            print('end_cashout() return ', end='')
            if ret == 0:
                print('0=success launched request')
            elif ret == -1:
                print('-1=API token lost or not given')
            elif ret == -2:
                print('-2=existing cashout phase 1 transaction')
            elif ret == -3:
                print('-3=existing cashout phase 2 transaction')
            elif ret == -4:
                print('-4=phase 1 not complete')
            elif ret == -9:
                print('-9=inner error')
            else:
                print('unknown', ret)

            if ret == 0:
                while True:
                    json_data = webapi.wait_end_cashout_result(timeout_sec=0.2)
                    if json_data['result_code'] != 1:
                        break
                    #print(".")
                print(json_data)    # for debug
                if json_data['result_code'] == 0:
                    print('0=got result (http status ', json_data['http_status_code'],')(status ',json_data['status'],')',sep='')
                elif json_data['result_code'] == -3:
                    print('-3=no prior request')
                elif json_data['result_code'] == -4:
                    print('-4=disorder error')
                else:
                    print('unknown', json_data['result_code'])
            print('Cash out transaction ended.')
            click_refresh()

    except Exception as e:
        print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        print('cash_out() except:', e)
        print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    finally:
        cash_out_lock.release()

#########################################################
# Handle global keyboard/key events
#########################################################

def on_button(func: str):
    print('button', func, 'pressed')

    try:
        if func == 'spin':
            #print('current url:', driver.current_url)
            #print('home url:', home_url)
            #print('<home_url_with_slash>/game:', home_url_with_slash + 'game')
            #print('driver.current_url.startswith(home_url)', driver.current_url.startswith(home_url))
            #print('driver.current_url.startswith(<home_url_with_slash>/game)', driver.current_url.startswith(home_url_with_slash + 'game'))
            if not driver.current_url.startswith(home_url) or driver.current_url.startswith(home_url_with_slash + 'game'):
                print('tap(space)')
                #kb_con.tap(' ')                     # 有效.
                #actions.send_keys(' ').perform()    # 無效. 之前有效.
                uinput_dev.emit_click(uinput.KEY_SPACE)
                '''
                with uinput.Device([uinput.KEY_SPACE]) as device:
                    time.sleep(0.02)
                    device.emit_click(uinput.KEY_SPACE)
                '''

        elif func == 'cashout':
            cash_out()
            pass

        elif func == 'home':
            # Just switch to 'Home' tab.
            # If it's not in home page or in game, must reload (but need not auto-login)
            if len(driver.window_handles) > 2:
                for handle in driver.window_handles:
                    if handle not in [game_tab_handle, setting_tab_handle]:
                        driver.switch_to.window(handle)
                        driver.close()
                        time.sleep(0.1)
            driver.switch_to.window(game_tab_handle)
            if driver.current_url != home_url:
                print('Reload HOME page')
                #driver.switch_to.window(game_tab_handle)
                #不需要重新登入, 透過 refresh 即可.
                #driver.get(home_url_with_slash + token)
                driver.get(home_url)
                # 避免 right click 叫出 contentmenu 以及避免按下若干種按鍵. 
                driver.execute_script('document.addEventListener("contextmenu", function(e) {e.preventDefault();});')
                driver.execute_script('document.addEventListener("keydown", e => {if(e.key=="F3"||e.key=="F6"||e.key=="F7"||e.key=="F10"||e.key=="F11"||e.key=="F12"){e.preventDefault();}});')

        elif func == 'vol+':
            #os.system('amixer set Master 5%+ | grep "^  Mono:"')
            subprocess.run(['amixer', 'set', 'Master', '5%+'], capture_output=True)

        elif func == 'vol-':
            #os.system('amixer set Master 5%- | grep "^  Mono:"')
            subprocess.run(['amixer', 'set', 'Master', '5%-'], capture_output=True)

        elif func == 'refresh':
            click_refresh()

        elif func == 'operator':
            cash_in()
            '''
            driver.switch_to.window(setting_tab_handle)
            print('URL:', driver.current_url)
            if not driver.current_url.startswith('https://127.0.0.1:631'):
                print('Reload SETTING page')
                driver.get('https://127.0.0.1:631')
            '''

    except Exception as e:
        print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        print('on_button() except:', e)
        print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    
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
# Routine threads/functions
#########################################################

def check_printer_status():
    status = printer.get_status()
    #print('check printer status=0x%X' % status, end='', sep='')
    status_list = printer.get_status_list()
    for msg in status_list:
        #print('[',msg,']', sep='', end='')
        notify(4000, 'printer-error', 'Receipt Printer', msg)
    #print()

def check_network_status():
    #print('check network:')
    t0 = time.time()
    try:
        ret = subprocess.run(['ping', '-n', '-c', '2', '-q', home_hostname], capture_output=True)
        #print('ping',home_hostname,'take',time.time() - t0,'sec')
        if ret.returncode == 0:
            t1 = time.time()
            ret = subprocess.run(['ping', '-n', '-c', '2', '-q', api_hostname], capture_output=True)
            #print('ping',api_hostname,'take',time.time() - t1,'sec')
        
        if ret.returncode != 0:
            #print(':NOGO (', time.time() - t0, ' sec)', sep='')
            notify(4000, 'network-error', 'Network', 'Disconnected with server')
        else:
            #print(':GO (', time.time() - t0, ' sec)', sep='')
            pass

    except OSError as e:
        print('except OSError:', e)
    except Exception as e:
        print('except:', e)

#########################################################
# Main Loop
#########################################################

loop = True
check_printer_thr = None
check_printer_duration = 5.0
check_printer_last_ts = time.time() - check_printer_duration
check_network_thr = None
check_network_duration = 5.0
check_network_last_ts = time.time() - check_network_duration

while loop:
    curr_ts = time.time()
    if curr_ts - check_printer_last_ts >= check_printer_duration:
        if check_printer_thr is not None:
            #print('printer join()', end='')
            check_printer_thr.join()
            #print(' done')
            check_printer_thr = None
        #print('check printer ', end='')
        try:
            check_printer_thr = threading.Thread(target=check_printer_status)
            check_printer_thr.start()
        except Exception as e:
            print(e)
            pass
        #print()
        check_printer_last_ts = curr_ts

    if curr_ts - check_network_last_ts >= check_network_duration:
        if check_network_thr is not None:
            #print('network join()')
            check_network_thr.join()
            #print('network join() done')
            check_network_thr = None
        #print('check network ', end='')
        try:
            check_network_thr = threading.Thread(target=check_network_status)
            check_network_thr.start()
        except Exception as e:
            print(e)
            pass
        #print()
        check_network_last_ts = curr_ts
        
    # (tasks in main loop here)
    time.sleep(0.1)

print()

if check_printer_thr is not None:
    check_printer_thr.join()

if check_network_thr is not None:
    check_network_thr.join()

# release selenium (web driver)
print('notify web driver and printer to stop')
driver.quit()
printer.stop()

# release selenium (web driver)
print('release web driver')
webapi.join_all()

# release keyboard module
print('release kb module')
listener.stop()
if uinput_dev:
    uinput_dev.destroy()

# release printer module
print('release printer module')
try:
    printer.join()
except Exception as e:
    print('join printer threads except:', e)

#except KeyboardInterrupt:
#    driver.quit()
#    print("手動中斷，結束程式。")
