#!/usr/bin/env python
#-*- coding:UTF-8 -*-

from selenium import webdriver
import keyboard
import time

options = webdriver.FirefoxOptions()
options.add_argument("-private")
#options.add_argument("--kiosk")
driver = webdriver.Firefox(options=options)
driver.get("about:blank")

def main():
    global driver

    print("Press 'q' or 'Q' to quit.")
    while True:
        if keyboard.read_event(suppress=True).name in ['q', 'Q']:
            print("Exiting...")
            break
        elif keyboard.read_event(suppress=True).name in ['o', 'O']:
            print("Opening a new Firefox tab...")
            driver.execute_script("window.open('about:blank', '_blank');")
        elif keyboard.read_event(suppress=True).name == 'esc':
            print("Closing the current Firefox tab...")
            driver.execute_script("window.close();")
        time.sleep(0.01)
    
    driver.quit();
    print("Firefox closed.")

    exit(0)

if __name__ == "__main__":
    main()