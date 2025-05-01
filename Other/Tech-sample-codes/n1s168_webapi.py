#!/usr/bin/env python
#-*- coding:UTF-8 -*-
#
# n1s168_webapi.py
#
#

import os, time, sys, datetime
import threading
import requests

class n1s168_webapi {
    def __init__(self, api_base_url:str = 'https://api.n1s168.com', token:str|None = None):
        self.api_base_url = api_base_url + ('' if api_base_url[-1] == '/' else '/')
        self.token = token
        
        # cashin
        self.b_cashin_in_progress = False
        self.req_cashin_event = threading.Event()
    
    # fetch_token()
    #
    # return: json object (dictionary)
    # {
    #   result_code: integer 0=success, -1=inner error, -2=http status code is not 2xx, -3=status field is false
    #   http_status_code: integer -  2xx=success, -1=inner error, -2=status field is false, (others)=http status code (failure, <>2xx)
    #   # below is valid only if http_status_code <> -1
    #   token: string - JWT authentication token
    #   data: {
    #     id: integer - User ID
    #     name: string - User name (may be empty)
    #     account: string - User account identifier
    #     credit: string - User credit balance
    #     user_level: integer - User level
    #   }
    #   ip: string - client IP
    #   status: boolean - True or False
    # }
    #
    def fetch_token(self, account:str, password:str):
        url = self.api_base_url + 'api/v1/user/login/'
        headers = {"Content-Type": "application/json"}
        data = { "account": account, "password": password }

        response = None
        try:
            response = requests.post(url, json=data, headers=headers)
        except requests.exceptions.ConnectionError as e:
            print('e)
        except requests.exceptions.Timeout as e:
            print(e)
        except requests.exceptions.TooManyRedirects as e:
            print(e)
        except Exception as e:
            print(e)
        
        if response is None:
            return {'result_code': -1}
        
        json_data = response.json()
        json_data['http_status_code'] = response.status_code
        if response.status_code < 200 and response.status_code >= 300:
            json_data['result_code'] = -2
        elif json_data['status']:
            json_data['result_code'] = -3
        else:
            json_data['result_code'] = 0

        self.token = json_data['token']
        return json_data

    # req_cashin(self, value)
    # input:
    #   value: how much (dollar) to cash in
    # return:
    #   0=successfully launched the request (enter in-progress state). 
    #     Please use req_cashin_result() later regularly to fetch result
    #   -1=existing cashin transaction already
    def req_cashin(self, value:float) -> int:
        if self.b_cashin_in_progress:
            return -1

        self.req_cashin_event.clear()
        url = self.api_base_url + 'api/v1/deposit/jtype/req-cashin'
        headers = {
          "Content-Type": "application/json",
          "Authorization": "Bearer " + self.token
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
        
        #print('req headers:', headers)
        #print('req body', data)
        
        # Raise thread
        #(todo)
        # when got the result, self.req_cashin_event.clear() to notify caller thread
    
    # req_cashin_result(self)
    # return: json object
    # { 
    #   result_code: 1=still in progress, 0=success, -1=inner error, -2=no prior request
    #   http_status_code: (for reference. may be 401)
    #   # refer to the below only if result_code==0;
    #   status: string - "0-OK" 表示成功, 
    #                    "1-OVER LIMIT" 表示已經超過 CREDITS 上限, 無法接收更多.
    #                    "2-OCCUPIED" 表示已被網頁玩家占用. 不算是錯誤. (reserved)
    #                    "6-BAD DATA/FORMAT", 
    #                    "7-OUT OF SERVICE", 
    #                    "9-OTHER ERROR"
    #   currenty: string - for reference only
    #   value: float - for reference only
    #   TXID: string - UUID for this transaction
    #   dateTime: string - pending 紀錄建立時間 格式: 格式: "<YYYY>-<MM>-<DD>T<HH>:<mm>:<SS>[.<sss>]Z"
    # }
    def req_cashin_result(self):
        if self.b_cashin_in_progress:
            return {"result_code": -1}
        
        self.req_cashin_event.clear()
        if self.token is None or len(self.token) == 0:
            return {"result_code": 0, "status": "9-OTHER ERROR", "http_status_code": 401}




#
# This is for testing only
# Return None or <token> string
#
def __read_token() -> str | None:
    token = None
    if os.path.isfile('./token.txt'):
        try:
            with open('./token.txt', "r") as f:
                for line in f:
                    token = line.strip()
                    print('Read token: (',token,')',sep='')
                    break
        except Exception as e:
            print(e)
    else:
        print('token file ./token.txt not found')

    return token


if __name__ == '__main__':
    print('Input a number with [enter]:')
    print('<1> get token and generate ./token.txt')
    print('<2> do cash in')
    print('<3> do cash out')
    
    func = input()
    
    if func[0] == '1':
        print('Get API token example')
        print('Input parameters (may input partial)')
        print('<account> <password> <api_base_url>:')
        args = input()
        argv = args.strip().split()
        argv_len = len(argv)
        
        account = argv[0] if argv_len > 0 else 'ITgame01'
        password = argv[1] if argv_len > 1 else 'ITgame01'
        api_base_url = argv[2] if argv_len > 2 else 'https://api.n1s168.com'
        webapi = n1s168_webapi(api_base_url)
        
        json_data = webapi.fetch_token(account, password)
        print('Return:')
        print(json_data)
      
        if json_data['result_code'] == 0:
            url = 'https://demo.n1s168.com/#/' + json_data['token']
            print('url:', url)
      
            print('Generate file ./token.txt ...', end='')
            try:
                with open("token.txt", "w") as f:
                    # Write bytes to file
                    f.write(json_data['token'])
                    f.write('\n')
                    f.write(url)
                    f.write('\n')
            except:
                print('write failed!')
                os._exit(1)
   
    elif func[0] == '2':
        print('Do cash-in')
        print('Input parameters (may input nothing for 5.0 dollars by default)')
        print('<dollar(float)> <api_base_url>:')
        args = input()
        argv = args.strip().split()
        argv_len = len(argv)
        value = float(argv[0]) if argv_len > 0 else 5.0
        api_base_url = argv[1] if argv_len > 1 else 'https://api.n1s168.com'

        token = __read_token()
        if token is None:
            os._exit(1)
        webapi = n1s168_webapi(api_base_url, token)
        
        # raise request. will run in a background thread.
        webapi.req_cashin(value)
        # wait or check event state
        #   blocking: json_data.event_cashin.wait([<timeout>])
        #   non-blocking: json_data.event_cashin.is_set()
        # json_data.event_cashin.is_set()
        while json_data.req_cashin_event.wait(0.2):
            json_data = webapi.req_cashin_result(value)
            if json_data['result_code'] == 0
            print(".")

        
        
        
      
      
      
    print('Done')
   