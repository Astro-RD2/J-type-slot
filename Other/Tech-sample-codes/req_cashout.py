#!/usr/bin/env python
#-*- coding:UTF-8 -*-

import os, time, sys
import datetime
import requests
#from requests_toolbelt.utils import dump      # for debug

#####################################################
# PHASE 1
#####################################################
print('[BEGIN PHASE 1]')
url = 'https://api.n1s168.com/api/v1/withdrawal/jtype/req-cashout'
headers = {
  "Content-Type": "application/json",
  "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiNjIxNGRhZDBiZDNmYzIyZDZjMzMzMmM2OTAzNjUxOGNhNDE3ODBkOWRhMWM3MzE1MmFjZGUzMTNmNTY5OTI0NWM0MjdhOTYzM2JlNmQwNDYiLCJpYXQiOjE3NDU5NjA0ODAuMTQ3NjI1LCJuYmYiOjE3NDU5NjA0ODAuMTQ3NjI5LCJleHAiOjE3Nzc0OTY0ODAuMTMzNTk5LCJzdWIiOiIxOTY0NCIsInNjb3BlcyI6W119.iWFbul-X3s3i__WbeK5aOLzJEV2m85Xf1QDnTM2Z73C2LKmuJ53CAKTqOiSJ2tfoJTLEcqC8F0LOnif3RYh090cigPp5Zw9jKb20EEvdQbCr6sTcgQVRpqr1-jT_iRWdbAUEIDLC_q1frQ4UR8jdhvfNB8TCNwXwoRMwvY8wphSziVz7XGCzny72Jp4WGXNUGHIXVgoWHE492Y14ZYnSoWf0VADwGJZ39-RCxHi191rREc84rWdTpFijTz63Gxl9adaHjZ8Cw355xP9RLJIZWRU2ar89dqkqtBPMnkPzgPFXyBMl2b_zoCfbV_kAHQvZ2xaSvMoSMPJFH2jBWn1fE-4b-9APW6PUmxBWJE-lsqgalLtkcK6Mc7fhxCR5yZS-Hq3XhvcbixYsH6F5e09QZF_F8joog1DsjIGalwaF5G1POQwsbkNsQ6uuiqrtFdERLThCrpUwkEovUUES7yol5eWmaFuI042mTpVbygNIvBVGQKDqxKsPapCr7iLf7K4N0nJt8U9sMrx3ZYlVDvEkST-PtGqHqw6KqoBSEswHnJXXsic9W-zylXlCfHFNFsOhUzrw6tImB-F4864i9I_-_rwIFsJDwbly9bOI_hexcQpSpPszeQXrDWrlfYF2xtKktyiG_RoHrmS4n5Wl9yqKxISZGe12EpHaZfJVr8llQR0"
}
data = {
  "action": "req-cashout", 
  #"currency": "USD",
  #"value": 5.00,
  "dateTime": datetime.datetime.now(datetime.timezone.utc).strftime('%FT%T.%f')[:-3] + 'Z'
    # datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    # https://stackoverflow.com/questions/2150739/iso-time-iso-8601-in-python
    # e.g. 2024-08-01T04:38:47.731215+00:00
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

print('simulate printing...')
time.sleep(4)

url = 'https://api.n1s168.com/api/v1/withdrawal/jtype/end-cashout'
headers = {
  "Content-Type": "application/json",
  "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiNjIxNGRhZDBiZDNmYzIyZDZjMzMzMmM2OTAzNjUxOGNhNDE3ODBkOWRhMWM3MzE1MmFjZGUzMTNmNTY5OTI0NWM0MjdhOTYzM2JlNmQwNDYiLCJpYXQiOjE3NDU5NjA0ODAuMTQ3NjI1LCJuYmYiOjE3NDU5NjA0ODAuMTQ3NjI5LCJleHAiOjE3Nzc0OTY0ODAuMTMzNTk5LCJzdWIiOiIxOTY0NCIsInNjb3BlcyI6W119.iWFbul-X3s3i__WbeK5aOLzJEV2m85Xf1QDnTM2Z73C2LKmuJ53CAKTqOiSJ2tfoJTLEcqC8F0LOnif3RYh090cigPp5Zw9jKb20EEvdQbCr6sTcgQVRpqr1-jT_iRWdbAUEIDLC_q1frQ4UR8jdhvfNB8TCNwXwoRMwvY8wphSziVz7XGCzny72Jp4WGXNUGHIXVgoWHE492Y14ZYnSoWf0VADwGJZ39-RCxHi191rREc84rWdTpFijTz63Gxl9adaHjZ8Cw355xP9RLJIZWRU2ar89dqkqtBPMnkPzgPFXyBMl2b_zoCfbV_kAHQvZ2xaSvMoSMPJFH2jBWn1fE-4b-9APW6PUmxBWJE-lsqgalLtkcK6Mc7fhxCR5yZS-Hq3XhvcbixYsH6F5e09QZF_F8joog1DsjIGalwaF5G1POQwsbkNsQ6uuiqrtFdERLThCrpUwkEovUUES7yol5eWmaFuI042mTpVbygNIvBVGQKDqxKsPapCr7iLf7K4N0nJt8U9sMrx3ZYlVDvEkST-PtGqHqw6KqoBSEswHnJXXsic9W-zylXlCfHFNFsOhUzrw6tImB-F4864i9I_-_rwIFsJDwbly9bOI_hexcQpSpPszeQXrDWrlfYF2xtKktyiG_RoHrmS4n5Wl9yqKxISZGe12EpHaZfJVr8llQR0"
}
data = {
  "action": "end-cashout", 
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

