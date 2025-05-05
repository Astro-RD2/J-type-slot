import time, os
import keyboard
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 啟動 Firefox
if os.path.isfile('./geckodriver'):
    service = Service(executable_path='./geckodriver')
elif os.path.isfile('/snap/bin/firefox.geckodriver'):
    service = Service(executable_path='/snap/bin/firefox.geckodriver')
else:
    print('Driver for firefox not found!')
    sys._exit(1)
#service = Service(executable_path='C:/selenium/geckodriver.exe', log_output=None)
driver = webdriver.Firefox(service=service)

# 開啟網頁
driver.get("https://demo.n1s168.com/#/")

wait_obj = WebDriverWait(driver, 10)

from selenium.webdriver.common.action_chains import ActionChains

try:
    while True:
        print('[0] - auto login')
        print('[1] - find refresh and click it')
        print('[2] - find nonpresent element (error situation)')
        print('[3~5] - find login and click it (3 ways)')
        print('[q] - quit')
        func = input()

        if func == '0':
            # Auto login
            driver.get('https://demo.n1s168.com/#/eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiMjZlYjUxM2YzYWUxOGU1ZDA3MzEyNmQ3YTUwNjEyMzkwYjY5NWExN2I3OGU3NTYxMjFjMGM0MzdlMmE3NjE4N2Q3ZjI2YjU4ZmI2MzVmYzIiLCJpYXQiOjE3NDYzMDQ0MjguODc1MzA4LCJuYmYiOjE3NDYzMDQ0MjguODc1MzEyLCJleHAiOjE3Nzc4NDA0MjguODY1MjI1LCJzdWIiOiIxOTY0NCIsInNjb3BlcyI6W119.R4AIJfbcIPZy-AOpTnXH9JLMyQ43svB1yKfpnqvxhZoTWKeqtYlpCjlp2vVFnDlO6CKCh4lJ0rmhlFSnAkxMnMoDtdhY3QW0gqs8kAc-jGg0aTD8vF90o3f82xlFyVYaCy_hZRDNuldWGJGKQEygdwBVgHrEi3xnhiV0K2dCM_7kooIVooOqSOWmLelqY1D1A5KX6EUfH53jjc3jBkDik9TRdX8h_2OSxposoTF3m2bRpitqJbrLkCO4dU3NM0nxTU11mX7fWM_PNySu7JZ8HXdXHnfCxn3xvpq3Gr3U3TyNxlw_fiWgpt5_dV40uUAI7HaPL-mL6pUM03e3SeXigJ8IXAaqAwjj72ScTpiFhKsb09j3DjKx_t3AtQkxllrkXcOs6Qox5H28J88HzxlH_NEDVhBAWHrKasdKAGBIRtVz_15RsVrRDD-v3jSQ6YHP84Ako2S7fEiYEHN9fy0fEXgiFBAKTxNiTvlWceBcUqKgQCLTNv9BWRQTX774YdxTuhdEO4dhhxKanKGBRadqOKsund4LDPRm3lMDyJrWKKLNZgWEp_FiSBXpeR6SaaaS3U8GMbGicKk0v8bfthVGsYuxxmXbQkE9F6IzwogTL5PPZKfl1nhgqhSQ5aKXFVuM9D9jtC15VCynjChEFQ2pSnFzAM8VTCqs-skSbkJXA8A')
            # below, always be zero
            # WebDriverWait() just define a wait object, used for until()
            #ts = time.time()
            #WebDriverWait(driver, 10)
            #print('take',time.time() - ts,'to load page')

        elif func == '1':
            # Refresh balance入
            try:
                # 找 refresh 按鈕
                ts = time.time()
                try:
                    #refresh_button = driver.find_element(By.CSS_SELECTOR, 'i.mdi-refresh.mdi.v-icon.notranslate')
                    refresh_button = driver.find_element(By.CSS_SELECTOR, 'i.mdi-refresh.mdi.v-icon')
                    '''
                    refresh_button = wait_obj.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'i.mdi-refresh.mdi.v-icon.notranslate')) #text-white.pr-\\[20px\\].cursor-pointer"))
                    )
                    '''
                    print('take',time.time() - ts,'to load page')
                    # 印出按鈕資訊
                    print("Login button found:", refresh_button)
                    print("Button text:", refresh_button.text)
                    refresh_button.click()
                    print("refresh click")
                except selenium.common.exceptions.WebDriverException as e:
                    print('take',time.time() - ts,'to load page')
                    print('web driver except:', e)
                except Exception as e:
                    print('take',time.time() - ts,'to load page')
                    print('except:', e)
                  
            except Exception as e:
                print("refresh button not found", e)
            time.sleep(0.3)  # 防止重複觸發

        elif func == '2':
            # 失敗. Refresh balance入
            try:
                # 找 refresh 按鈕
                ts = time.time()
                try:
                    refresh_button = wait_obj.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'xxxxxxxxxxxxxxxxxxxxxxxxx')) #text-white.pr-\\[20px\\].cursor-pointer"))
                    )
                    print('take',time.time() - ts,'to load page')
                    # 印出按鈕資訊
                    print("Login button found:", refresh_button)
                    print("Button text:", refresh_button.text)
                    refresh_button.click()
                    print("refresh click")
                except selenium.common.exceptions.WebDriverException as e:
                    print('take',time.time() - ts,'to load page')
                    print('web driver except:', e)
                except Exception as e:
                    print('take',time.time() - ts,'to load page')
                    print('except:', e)
                  
            except Exception as e:
                print("refresh button not found", e)
            time.sleep(0.3)  # 防止重複觸發

        elif func == '3':  # keyboard.is_pressed('1'):
            # 點擊登入
            try:
                # 找登入按鈕
                login_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.text-white.pr-\\[20px\\].cursor-pointer"))
                )
                # 印出按鈕資訊
                print("Login button found:", login_button)
                print("Button text:", login_button.text)
                login_button.click()
                print("Login click")
            except Exception as e:
                print("Login button not found", e)
            time.sleep(0.3)  # 防止重複觸發

        elif func == '4': # keyboard.is_pressed('2'):
            # 點擊登入
            try:
                # 找登入按鈕
                login_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.text-white.pr-\\[20px\\].cursor-pointer"))
                )
                # 印出按鈕資訊
                print("Login button found:", login_button)
                print("Button text:", login_button.text)
                # 用 JavaScript 模擬點擊
                driver.execute_script("arguments[0].click();", login_button)
                print("JavaScript click")
            except Exception as e:
                print("Login button not found", e)
            time.sleep(0.3)  # 防止重複觸發

        elif func == '5': # keyboard.is_pressed('3'):
            # 點擊登入
            try:
                # 找登入按鈕
                login_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.text-white.pr-\\[20px\\].cursor-pointer"))
                )
                # 印出按鈕資訊
                print("Login button found:", login_button)
                print("Button text:", login_button.text)
                # 用滑鼠模擬方式點擊
                actions = ActionChains(driver)
                actions.move_to_element(login_button).click().perform()
                print("ActionChains click")
            except Exception as e:
                print("Login button not found", e)
            time.sleep(0.3)  # 防止重複觸發

        elif func in ['q', 'Q']:  # keyboard.is_pressed('q'):
            print("關閉整個 Firefox")
            driver.quit()
            break

except KeyboardInterrupt:
    driver.quit()
    print("手動中斷，結束程式。")