#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from selenium import webdriver
import keyboard
import time

options = webdriver.FirefoxOptions()
options.add_argument("-private")
driver = webdriver.Firefox(options=options)

def main():
    global driver
    tabs = {}

    dummy_tab_handle = driver.current_window_handle
    print(f'dummy handle: ', dummy_tab_handle)

    driver.execute_script("window.open('about:privatebrowsing', '_blank');")
    driver.switch_to.window(driver.window_handles[-1])
    tabs["tab1"] = driver.current_window_handle
    print("tab1 handle: ", tabs["tab1"])

    driver.switch_to.window(dummy_tab_handle)
    driver.close()
    time.sleep(2)

    driver.quit()
    print("Firefox closed.")

if __name__ == "__main__":
    main()