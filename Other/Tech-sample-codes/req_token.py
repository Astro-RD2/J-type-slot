#!/usr/bin/env python
#-*- coding:UTF-8 -*-

import os, time, sys
import requests

url = 'https://api.n1s168.com/api/v1/user/login/'
headers = {"Content-Type": "application/json"}
data = { "account": "ITgame01", "password": "ITgame01" }

try:
  response = requests.post(url, json=data, headers=headers)
  # if success, handle it ...
  if response.status_code == 200:
    json_data = response.json()    # 取得 json 物件.
except:
  print('failure, status_code', response.status_code)

print(response.json())  # 取得回應 body
url = 'https://demo.n1s168.com/#/' + json_data['token']
print(url)

with open("token.txt", "w") as binary_file:
    # Write bytes to file
    binary_file.write(json_data['token'])
    binary_file.write('\n')
    binary_file.write(url)
    binary_file.write('\n')

print('done')
