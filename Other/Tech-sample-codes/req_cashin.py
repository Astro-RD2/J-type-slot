#!/usr/bin/env python
#-*- coding:UTF-8 -*-

import os, time, sys
import datetime
import requests
#from requests_toolbelt.utils import dump      # for debug

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

# read value from 
value = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0

#####################################################
# PHASE 1
#####################################################
print('[BEGIN PHASE 1]')
url = 'https://api.n1s168.com/api/v1/deposit/jtype/req-cashin'
headers = {
  "Content-Type": "application/json",
  "Authorization": "Bearer " + token
}
data = {
  "action": "req-cashin", 
  "currency": "USD",
  "value": value,
  "dateTime": datetime.datetime.now(datetime.timezone.utc).strftime('%FT%T.%f')[:-3] + 'Z'
    # datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    # https://stackoverflow.com/questions/2150739/iso-time-iso-8601-in-python
    # e.g. 2024-08-01T04:38:47.731Z
}
print('req headers:', headers)
print('req body', data)

do_phase2 = False
try:
  response = requests.post(url, json=data, headers=headers)
  # if success, handle it ...
  if response.status_code >= 200 and response.status_code < 300:
    json_data = response.json()    # 取得 json 物件.
    print('response body:', json_data)  # 印出回應 body
    print('status:', json_data['status'])
    if json_data['status'][:2] == '0-':
        do_phase2 = True
  else:
    print('failure! status_code:', response.status_code)
except Exception as e:
  print('except:', e)

if not do_phase2:
  os._exit(1)

#####################################################
# PHASE 2
#####################################################
print('[BEGIN PHASE 2]')
TX_id = json_data['TXID']
value = json_data['value']

time.sleep(3)

url = 'https://api.n1s168.com/api/v1/deposit/jtype/end-cashin'
headers = {
  "Content-Type": "application/json",
  "Authorization": "Bearer " + token
}
data = {
  "action": "end-cashin", 
  "currency": "USD",
  "value": value,
  "TXID": TX_id,
  "dateTime": datetime.datetime.now(datetime.timezone.utc).strftime('%FT%T.%f')[:-3] + 'Z'
}
print('req headers:', headers)
print('req body', data)

try:
  response = requests.post(url, json=data, headers=headers)
  # if success, handle it ...
  if response.status_code >= 200 and response.status_code < 300:
    json_data = response.json()    # 取得 json 物件.
    print('response body:', json_data)  # 印出回應 body
    print('status:', json_data['status'])
  else:
    print('failure! status_code:', response.status_code)
except Exception as e:
  print('except:', e)

