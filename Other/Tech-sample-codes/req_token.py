#!/usr/bin/env python
#-*- coding:UTF-8 -*-

import os, time, sys
import requests

g_response = None

# return: json object
# {
#   http_status_code: integer   -1=inner error, (others)=http status code (2xx=success, others=failure)
#   # below is valid only if http_status_code==200
#   id: integer - User ID
#   name: string - User name (may be empty)
#   account: string - User account identifier
#   credit: string - User credit balance
#   user_level: integer - User level
# }
#
def get(account: str, password: str, api_base_url: str):
  url = api_base_url + ('' if api_base_url[-1] == '/' else '/') + 'api/v1/user/login/'
  headers = {"Content-Type": "application/json"}
  data = { "account": account, "password": password }

  response = None
  json_data = None

  try:
    response = requests.post(url, json=data, headers=headers)
  except requests.exceptions.ConnectionError as e:
    print(e)
  except requests.exceptions.Timeout as e:
    print(e)
  except requests.exceptions.TooManyRedirects as e:
    print(e)
  except Exception as e:
    print(e)
  
  if response is None:
    return {'http_status_code': -1}
  elif response.status_code < 200 and response.status_code >= 300:
    return {'http_status_code': response.status_code}
  
  # if success, handle it ...
  json_data = response.json()

  # add http_status_code to object
  json_data['http_status_code'] = response.status_code

  return json_data


if __name__ == '__main__':
  print('Get API token example')

  argv_len = len(sys.argv)
  account = sys.argv[1] if argv_len > 1 else 'ITgame01'
  password = sys.argv[2] if argv_len > 2 else 'ITgame01'
  api_base_url = sys.argv[3] if argv_len > 3 else 'https://api.n1s168.com'
  json_data = get(account, password, api_base_url)
  print('Return:')
  print(json_data)
  
  if json_data['http_status_code'] == 200:
    url = 'https://demo.n1s168.com/#/' + json_data['token']
    print('url:', url)

    print('Write to file ./token.txt ...', end='')
    with open("token.txt", "w") as binary_file:
      # Write bytes to file
      binary_file.write(json_data['token'])
      binary_file.write('\n')
      binary_file.write(url)
      binary_file.write('\n')

  print('Done')
