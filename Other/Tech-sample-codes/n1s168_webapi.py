#!/usr/bin/env python
#-*- coding:UTF-8 -*-
#
# n1s168_webapi.py
#
#

import os, time, sys, datetime
import threading
import requests

class n1s168_webapi:
    def __init__(self, api_base_url:str = 'https://api.n1s168.com', currency:str = 'USD', token:str = ''):
        self.__api_base_url:str = api_base_url + ('' if api_base_url[-1] == '/' else '/')
        self.__token:str = token
        self.__currency:str = currency
        
        # for cashin
        self.__ci_thr = None
        self.ci_event = threading.Event()   # monitor this event right after call req_cachin()
                                            # DOWN when request, UP when webapi finished, DOWN when result was got
        self.__ci_b_req_idle = threading.Event() # use Event object as boolean variable
        
        # for cashout
        self.__co_thr = None
        self.co_event = threading.Event()   # monitor this event right after call req_cachin()
        self.__co_b_req_idle = threading.Event()
        self.reset_all()

    def reset_all(self):
        # for cashin
        if self.__ci_thr is not None:
            try:
                self.__ci_thr.join()
            except:
                print('join thread fail!')
                pass
            self.__ci_thr = None

        self.ci_event.clear()               # monitor this event right after call req_cachin()
                                            # DOWN when request, UP when webapi finished, DOWN when result was got
        self.__ci_b_req_idle.set()          # DOWN when request, UP when webapi finished
        self.__ci_value:float = 0.0         
        #--
        self.__ci_TXID:str = ''
        self.__ci_json_data = None          # json data from API server

        # for cashout
        if self.__co_thr is not None:
            try:
                self.__co_thr.join()
            except:
                print('join thread fail!')
                pass
            self.__co_thr = None
        self.co_event.clear()               # monitor this event right after call req_cachin()
        self.__co_b_req_idle.set()          # DOWN when request, UP when webapi finished
        #--
        self.__co_TXID:str = ''
        self.__co_value:float = 0.0
        self.__co_json_data = None          # json data from API server

    def set_api_base_url(self, api_base_url:str = 'https://api.n1s168.com'):
        if len(api_base_url) > 0:
            self.__api_base_url = api_base_url + ('' if api_base_url[-1] == '/' else '/')

    def set_token(self, token:str = ''):
        self.__token = token

    def request(self, url:str, data:dict, headers:None|dict, timeout_sec:float|None=None):
        response = None
        try:
            if timeout_sec is None:
                response = requests.post(url, json=data, headers=headers)
            else:
                response = requests.post(url, json=data, headers=headers, timeout=timeout_sec)
        except requests.exceptions.ConnectionError as e:
            print(e)
        except requests.exceptions.HTTPError as e:
            print(e)
        except requests.exceptions.Timeout as e:
            print(e)
        except requests.exceptions.TooManyRedirects as e:
            print(e)
        except Exception as e:
            print(e)
        except:
            print('request: unknown except')
        return response
    
    # fetch_token()
    #
    # return: json object (dictionary)
    # {
    #   "result_code": int - 0=success, 
    #                       -1=API request error (cannot raise request.post())
    #                       -2=http status code is not 2xx, 
    #                       -3=status field is false
    #   "http_status_code": int
    #   # below is valid only if http_status_code <> -1
    #   "token": str - JWT authentication token
    #   "data": {
    #     "id": int - User ID
    #     "name": str - User name (may be empty)
    #     "account": str - User account identifier
    #     "credit": str - User credit balance
    #     "user_level": int - User level
    #   }
    #   "ip": str - client IP
    #   "status": bool - True or False
    # }
    #
    def fetch_token(self, account:str, password:str) -> dict:
        self.__token = ''
        url = self.__api_base_url + 'api/v1/user/login/'
        headers = {"Content-Type": "application/json"}
        data = { "account": account, "password": password }

        response = self.request(url, data, headers, timeout_sec=15.0)
        if response is None:
            return {'result_code': -1}

        json_data = response.json()
        json_data['http_status_code'] = response.status_code
        if response.status_code < 200 or response.status_code >= 300:
            json_data['result_code'] = -2
        elif not json_data['status']:
            json_data['result_code'] = -3
        else:
            json_data['result_code'] = 0

        self.__token = json_data['token']
        return json_data

    #################################################################
    # state machine for cashin:
    #   BEFORE PHASE 1: (event=X,    b_req_idle=True*,  TXID=X,      json_data=X)
    #   DURING PHASE 1: (event=DOWN, b_req_idle=False,  TXID='',     json_data=None)
    #    WEBAPI RESULT: (event=UP,   b_req_idle=True,   TXID='',     json_data=<json data>)
    #       GOT RESULT: (event=UP,   b_req_idle=True*,  TXID='',     json_data=<json data>*) if pending
    #               OR: (event=DOWN, b_req_idle=True,   TXID='',     json_data=None) if failure
    #               OR: (event=DOWN, b_req_idle=True,   TXID=<txid>, json_data=None) if success, may go to PHASE 2
    #  
    #   BEFORE PHASE 2: (event=DOWN, b_req_idle=True*,  TXID=<txid>*,json_data=X)
    #   DURING PHASE 2: (event=DOWN, b_req_idle=False,  TXID=<txid>, json_data=None)
    #    WEBAPI RESULT: (event=UP,   b_req_idle=True,   TXID=<txid>, json_data=<json data>) including retry, or got determined result
    #       GOT RESULT: (event=UP,   b_req_idle=True*,  TXID=<txid>, json_data=<json data>*) if pending
    #               OR: (event=DOWN, b_req_idle=True,   TXID='',     json_data=None*) if failure/success
    #
    #################################################################
    
    # req_cashin(self, value)
    # input:
    #   value: how much (dollar) to cash in
    # return:
    #   0=successfully launched the request (enter in-progress state). 
    #     Please use wait_req_cashin_result() later regularly to fetch final result
    #   -1=API token lost or not given (nothing changed)
    #   -2=existing cashin phase 1 transaction (nothing changed)
    #   -3=existing cashin phase 2 transaction (nothing changed)
    #   -9=inner error (including 0/negative 'value')
    def req_cashin(self, value:float) -> int:
        if not self.__ci_b_req_idle.is_set():
            return -2 if self.__ci_TXID == '' else -3
        if self.__ci_thr is not None:
            try:
                self.__ci_thr.join()
            except:
                print('join thread fail!')
                pass
            self.__ci_thr = None

        if len(self.__token) == 0:
            return -1
        if value < 0.00000001:
            return -9

        self.__ci_b_req_idle.clear()   # False
        self.ci_event.clear()   # DOWN
        self.__ci_value = value
        self.__ci_TXID = ''
        self.__ci_json_data = None

        url = self.__api_base_url + 'api/v1/deposit/jtype/req-cashin'
        headers = {
          "Content-Type": "application/json",
          "Authorization": "Bearer " + self.__token
        }
        data = {
          "action": "req-cashin", 
          "currency": self.__currency,
          "value": value,
          "dateTime": datetime.datetime.now(datetime.timezone.utc).strftime('%FT%T.%f')[:-3] + 'Z'
            # datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
            # https://stackoverflow.com/questions/2150739/iso-time-iso-8601-in-python
            # e.g. 2024-08-01T04:38:47.731Z
        }

        def __thread_P1(url, data, headers):      # class n1s168_webapi
            nonlocal self
            #nonlocal url, headers, data
            
            response = self.request(url, data, headers, timeout_sec=15.0)
            if response is None:
                self.__ci_json_data = {'result_code': -1}
            elif response.status_code < 200 and response.status_code >= 300:
                self.__ci_json_data = {'result_code': -2, 'http_status_code': response.status_code}
            else:
                json_data = response.json()
                #self.__ci_json_data = response.json()
                json_data['result_code'] = 0
                json_data['http_status_code'] = response.status_code
                self.__ci_json_data = json_data
            self.ci_event.set()         # UP
            self.__ci_b_req_idle.set()  # True

        # def request(self, url:str, json_data:dict, headers:None|dict)
        try:
            self.__ci_thr = threading.Thread(target=__thread_P1, args=(url, data, headers,))
            self.__ci_thr.start()
        except:
            print('cannot raise cashin phase-1 thread!')
            self.__ci_thr = None
            self.__ci_b_req_idle.set()  # True
            return -9
        return 0

    # wait_req_cashin_result(self, timeout_sec)
    # Input:
    #    timeout_sec: await how many seconds to get the result. 
    #                 if not given, wait util getting result
    # return: json object
    # { 
    #   "result_code": int - 1=still in progress (nothing changed)
    #                        0=got result 
    #                       -1=API request error (cannot raise request.post())
    #                       -2=http status code is not 2xx, 
    #                       -3=no prior request (nothing changed)
    #                       -4=disorder error (should call wait_req_cashout_result)
    #   ## the below is valid only if result_code==0 or -2;
    #   "http_status_code": int - the status code returned from HTTP server. for reference only
    #   ## the below is valid only if result_code==0
    #   "status": str - "0-OK" 表示成功, 
    #                   "1-OVER LIMIT" 表示已經超過 CREDITS 上限, 此筆入金無法接受. 不算是錯誤.
    #                   "2-OCCUPIED" 表示已被網頁玩家占用. 不算是錯誤. (reserved)
    #                   "6-BAD DATA/FORMAT", 
    #                   "7-OUT OF SERVICE", 
    #                   "9-OTHER ERROR"
    #   "currency": str - for reference only
    #   "value": float - the money; for reference only
    #   "TXID": str - the unique Id of the transaction
    #   "dateTime": str - pending 紀錄建立時間. 格式: "<YYYY>-<MM>-<DD>T<HH>:<mm>:<SS>[.<sss>]Z"
    # }
    #
    # Remark:
    #   - if json["result_code"]==0 && json["status"][0]=='0' means procedure may go to phase 2
    def wait_req_cashin_result(self, timeout_sec:float|None = None) -> dict:
        if self.__ci_TXID != '':
            return {"result_code": -4}

        if not self.__ci_b_req_idle.is_set():
            if not self.__ci_b_req_idle.wait(timeout_sec):
                return {"result_code": 1}
        if self.__ci_thr is not None:
            try:
                self.__ci_thr.join()
            except:
                print('join thread fail!')
                pass
            self.__ci_thr = None

        if self.__ci_json_data is None:
            return {"result_code": -3}
        
        if self.__ci_json_data['result_code'] == 0 and self.__ci_json_data['status'][0] == '0':
            self.__ci_TXID = self.__ci_json_data['TXID']

        json_data = self.__ci_json_data
        self.__ci_json_data = None
        self.ci_event.clear()
        return json_data

    # end_cashin(self)
    # return:
    #   0=successfully launched the request (enter in-progress state). 
    #     Please use end_cashin_result() later regularly to fetch result
    #   -1=API token lost or not given (nothing changed)
    #   -2=existing cashin phase 1 transaction (nothing changed)
    #   -3=existing cashin phase 2 transaction (nothing changed)
    #   -4=Phase 1 not complete (nothing changed)
    #   -9=inner error
    def end_cashin(self) -> int:
        if not self.__ci_b_req_idle.is_set():
            return -2 if self.__ci_TXID == '' else -3
        if self.__ci_thr is not None:
            try:
                self.__ci_thr.join()
            except:
                print('join thread fail!')
                pass
            self.__ci_thr = None

        if len(self.__token) == 0:
            return -1
        if self.__ci_TXID == '' or self.__ci_value < 0.00000001:
            return -4

        self.__ci_b_req_idle.clear()   # False
        self.ci_event.clear()   # DOWN
        self.__ci_json_data = None

        url = self.__api_base_url + 'api/v1/deposit/jtype/end-cashin'
        headers = {
          "Content-Type": "application/json",
          "Authorization": "Bearer " + self.__token
        }
        data = {
          "action": "end-cashin", 
          "currency": self.__currency,
          "value": self.__ci_value,
          "TXID": self.__ci_TXID,
          "dateTime": datetime.datetime.now(datetime.timezone.utc).strftime('%FT%T.%f')[:-3] + 'Z'
            # datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
            # https://stackoverflow.com/questions/2150739/iso-time-iso-8601-in-python
            # e.g. 2024-08-01T04:38:47.731Z
        }

        def __thread_P2(url, data, headers):      # class n1s168_webapi
            nonlocal self
            #nonlocal url, headers, data
            last_ts = time.time() - 15.0

            while True:
                # retry interval is 10 seconds
                ts = time.time()
                delta = ts - last_ts
                if delta < 10.0:
                    time.sleep(10.0 - delta)
                last_ts = ts
                
                response = self.request(url, data, headers, timeout_sec=15.0)
                if response is None:
                    pass    # self.__ci_json_data = {'result_code': -1}
                elif response.status_code < 200 and response.status_code >= 300:
                    print('HTTP status code', response.status_code, '- none 2xx response!')
                    # self.__ci_json_data = {'result_code': -2, 'http_status_code': response.status_code}
                else:
                    json_data = response.json()
                    # if result has been determined, don't retry and return result
                    if json_data['status'][0] in ['0','1','6']:
                        json_data['result_code'] = 0
                        json_data['http_status_code'] = response.status_code
                        self.__ci_json_data = json_data
                        self.ci_event.set()         # UP
                        self.__ci_b_req_idle.set()  # True
                        break
                    print('status:', json_data['status'])

        # def request(self, url:str, json_data:dict, headers:None|dict)
        try:
            self.__ci_thr = threading.Thread(target=__thread_P2, args=(url, data, headers,))
            self.__ci_thr.start()
        except:
            print('cannot raise cashin phase-2 thread!')
            self.__ci_thr = None
            self.__ci_b_req_idle.set()  # True
            return -9
        return 0

    # wait_end_cashin_result(self, timeout_sec)
    # Input:
    #    timeout_sec: await how many seconds to get the result. 
    #                 if not given, wait util getting result
    # return: json object
    # { 
    #   "result_code": int - 1=still in progress (nothing changed)
    #                        0=got result 
    #                       -3=no prior request (nothing changed)
    #                       -4=disorder error (should call wait_req_cashin_result!!!)
    #   ## the below is valid only if result_code==0;
    #   "http_status_code": int - the status code returned from HTTP server. for reference only
    #                             (for non-2xx: do internal retry, won't be seen outside)
    #   "status": str - "0-OK" 表示成功.
    #                   "1-NO RECORD" 表示無對應入金紀錄, 可視為邏輯錯誤, 應結束流程,
    #                   "6-BAD DATA/FORMAT" (邏輯錯誤, 應結束流程),
    #                   "7-OUT OF SERVICE" (internal retry, won't be seen outside),
    #                   "9-OTHER ERROR" (internal retry, won't be seen outside)
    #   "currency": str - (for reference only)
    #   "value": float - the money; (for reference only)
    #   "TXID": str - the unique Id of the transaction; (for reference only)
    #   "dateTime": str - 事件/Complete 時間. 格式: "<YYYY>-<MM>-<DD>T<HH>:<mm>:<SS>[.<sss>]Z"
    # }
    # Remark:
    #   - if "result_code"<>1, the cashin transaction is always ended
    def wait_end_cashin_result(self, timeout_sec:float|None = None) -> dict:
        if self.__ci_TXID == '':
            return {"result_code": -4}

        if not self.__ci_b_req_idle.is_set():
            if not self.__ci_b_req_idle.wait(timeout_sec):
                return {"result_code": 1}
        if self.__ci_thr is not None:
            try:
                self.__ci_thr.join()
            except:
                print('join thread fail!')
                pass
            self.__ci_thr = None

        if self.__ci_json_data is None:
            return {"result_code": -3}
        
        self.__ci_TXID = ''
        json_data = self.__ci_json_data
        self.__ci_json_data = None
        self.ci_event.clear()
        return json_data

    #################################################################
    # state machine for cash-out:
    #   BEFORE PHASE 1: (event=X,    b_req_idle=True*,  TXID=X,      json_data=X)
    #   DURING PHASE 1: (event=DOWN, b_req_idle=False,  TXID='',     json_data=None)
    #    WEBAPI RESULT: (event=UP,   b_req_idle=True,   TXID='',     json_data=<json data>)
    #       GOT RESULT: (event=UP,   b_req_idle=True*,  TXID='',     json_data=<json data>*) if pending
    #               OR: (event=DOWN, b_req_idle=True,   TXID='',     json_data=None) if failure
    #               OR: (event=DOWN, b_req_idle=True,   TXID=<txid>, json_data=None) if success, may go to PHASE 2
    #  
    #   BEFORE PHASE 2: (event=DOWN, b_req_idle=True*,  TXID=<txid>*,json_data=X)
    #   DURING PHASE 2: (event=DOWN, b_req_idle=False,  TXID=<txid>, json_data=None)
    #    WEBAPI RESULT: (event=UP,   b_req_idle=True,   TXID=<txid>, json_data=<json data>) including retry, or got determined result
    #       GOT RESULT: (event=UP,   b_req_idle=True*,  TXID=<txid>, json_data=<json data>*) if pending
    #               OR: (event=DOWN, b_req_idle=True,   TXID='',     json_data=None*) if failure/success
    #
    #################################################################

    # req_cashout(self)
    # return:
    #   0=successfully launched the request (enter in-progress state). 
    #     Please use wait_req_cashout_result() later regularly to fetch final result
    #   -1=API token lost or not given (nothing changed)
    #   -2=existing cashout phase 1 transaction (nothing changed)
    #   -3=existing cashout phase 2 transaction (nothing changed)
    #   -9=inner error
    def req_cashout(self) -> int:
        if not self.__co_b_req_idle.is_set():
            return -2 if self.__co_TXID == '' else -3
        if self.__co_thr is not None:
            try:
                self.__co_thr.join()
            except:
                print('join thread fail!')
                pass
            self.__co_thr = None

        if len(self.__token) == 0:
            return -1

        self.__co_b_req_idle.clear()    # False
        self.co_event.clear()           # DOWN
        self.__co_value = 0.0
        self.__co_TXID = ''
        self.__co_json_data = None

        url = self.__api_base_url + 'api/v1/withdrawal/jtype/req-cashout'
        headers = {
          "Content-Type": "application/json",
          "Authorization": "Bearer " + self.__token
        }
        data = {
          "action": "req-cashout",
          "dateTime": datetime.datetime.now(datetime.timezone.utc).strftime('%FT%T.%f')[:-3] + 'Z'
            # datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
            # https://stackoverflow.com/questions/2150739/iso-time-iso-8601-in-python
            # e.g. 2024-08-01T04:38:47.731Z
        }

        def __thread_P1(url, data, headers):      # class n1s168_webapi
            nonlocal self
            #nonlocal url, headers, data
            
            response = self.request(url, data, headers, timeout_sec=15.0)
            if response is None:
                self.__co_json_data = {'result_code': -1}
            elif response.status_code < 200 and response.status_code >= 300:
                self.__co_json_data = {'result_code': -2, 'http_status_code': response.status_code}
            else:
                json_data = response.json()
                json_data['result_code'] = 0
                json_data['http_status_code'] = response.status_code
                self.__co_json_data = json_data
            self.co_event.set()         # UP
            self.__co_b_req_idle.set()  # True

        # def request(self, url:str, json_data:dict, headers:None|dict)
        try:
            self.__co_thr = threading.Thread(target=__thread_P1, args=(url, data, headers,))
            self.__co_thr.start()
        except:
            print('cannot raise cashout phase-1 thread!')
            self.__co_thr = None
            self.__co_b_req_idle.set()  # True
            return -9
        return 0

    # wait_req_cashout_result(self, timeout_sec)
    # Input:
    #    timeout_sec: await how many seconds to get the result. 
    #                 if not given, wait util getting result
    # return: json object
    # { 
    #   "result_code": int - 1=still in progress (nothing changed)
    #                        0=got result 
    #                       -1=API request error (cannot raise request.post())
    #                       -2=http status code is not 2xx, 
    #                       -3=no prior request (nothing changed)
    #                       -4=disorder error (should call wait_end_cashout_result)
    #   ## the below is valid only if result_code==0 or -2;
    #   "http_status_code": int - the status code returned from HTTP server. for reference only
    #   ## the below is valid only if result_code==0
    #   "status": str - "0-OK" 表示成功, 
    #                   "1-OVER LIMIT" 表示已經超過 CREDITS 上限, 此筆入金無法接受. 不算是錯誤.
    #                   "2-OCCUPIED" 表示已被網頁玩家占用. 不算是錯誤. (reserved)
    #                   "6-BAD DATA/FORMAT", 
    #                   "7-OUT OF SERVICE", 
    #                   "9-OTHER ERROR"
    #   "currency": str - for reference only
    #   "value": float - the money; for reference only
    #   "TXID": str - the unique Id of the transaction
    #   "dateTime": str - pending 紀錄建立時間. 格式: "<YYYY>-<MM>-<DD>T<HH>:<mm>:<SS>[.<sss>]Z"
    # }
    #
    # Remark:
    #   - if json["result_code"]==0 && json["status"][0]=='0' means procedure may go to phase 2
    def wait_req_cashout_result(self, timeout_sec:float|None = None) -> dict:
        if self.__co_TXID != '':
            return {"result_code": -4}

        if not self.__co_b_req_idle.is_set():
            if not self.__co_b_req_idle.wait(timeout_sec):
                return {"result_code": 1}
        if self.__co_thr is not None:
            try:
                self.__co_thr.join()
            except:
                print('join thread fail!')
                pass
            self.__co_thr = None

        if self.__co_json_data is None:
            return {"result_code": -3}
        
        if self.__co_json_data['result_code'] == 0 and self.__co_json_data['status'][0] == '0':
            if type(self.__co_json_data['value']) is str:
                self.__co_value = float(self.__co_json_data['value'])
            else:
                self.__co_value = self.__co_json_data['value']
            self.__co_TXID = self.__co_json_data['TXID']

        json_data = self.__co_json_data
        self.__co_json_data = None
        self.co_event.clear()
        return json_data

    # end_cashout(self)
    # return:
    #   0=successfully launched the request (enter in-progress state). 
    #     Please use wait_end_cashout_result() later regularly to fetch result
    #   -1=API token lost or not given (nothing changed)
    #   -2=existing cashout phase 1 transaction (nothing changed)
    #   -3=existing cashout phase 2 transaction (nothing changed)
    #   -4=Phase 1 not complete (nothing changed)
    #   -9=inner error
    def end_cashout(self) -> int:
        if not self.__co_b_req_idle.is_set():
            return -2 if self.__co_TXID == '' else -3
        if self.__co_thr is not None:
            try:
                self.__co_thr.join()
            except:
                print('join thread fail!')
                pass
            self.__co_thr = None

        if len(self.__token) == 0:
            return -1
        print('end_cashout:', type(self.__co_value))
        if self.__co_TXID == '' or self.__co_value < 0.00000001:
            return -4

        self.__co_b_req_idle.clear()    # False
        self.co_event.clear()           # DOWN
        self.__co_json_data = None

        url = self.__api_base_url + 'api/v1/withdrawal/jtype/end-cashout'
        headers = {
          "Content-Type": "application/json",
          "Authorization": "Bearer " + self.__token
        }
        data = {
          "action": "end-cashout", 
          "currency": self.__currency,
          "value": self.__co_value,
          "TXID": self.__co_TXID,
          "dateTime": datetime.datetime.now(datetime.timezone.utc).strftime('%FT%T.%f')[:-3] + 'Z'
            # datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
            # https://stackoverflow.com/questions/2150739/iso-time-iso-8601-in-python
            # e.g. 2024-08-01T04:38:47.731Z
        }

        def __thread_P2(url, data, headers):      # class n1s168_webapi
            nonlocal self
            #nonlocal url, headers, data
            last_ts = time.time() - 15.0

            while True:
                # retry interval is 10 seconds
                ts = time.time()
                delta = ts - last_ts
                if delta < 10.0:
                    time.sleep(10.0 - delta)
                last_ts = ts
                
                response = self.request(url, data, headers, timeout_sec=15.0)
                if response is None:
                    pass    # self.__co_json_data = {'result_code': -1}
                elif response.status_code < 200 and response.status_code >= 300:
                    print('HTTP status code', response.status_code, '- none 2xx response!')
                    # self.__co_json_data = {'result_code': -2, 'http_status_code': response.status_code}
                else:
                    json_data = response.json()
                    # if result has been determined, don't retry and return result
                    if json_data['status'][0] in ['0','1','6']:
                        json_data['result_code'] = 0
                        json_data['http_status_code'] = response.status_code
                        self.__co_json_data = json_data
                        self.co_event.set()         # UP
                        self.__co_b_req_idle.set()  # True
                        break
                    print('status:', json_data['status'])

        # def request(self, url:str, json_data:dict, headers:None|dict)
        try:
            self.__co_thr = threading.Thread(target=__thread_P2, args=(url, data, headers,))
            self.__co_thr.start()
        except:
            print('cannot raise cashout phase-2 thread!')
            self.__co_thr = None
            self.__co_b_req_idle.set()  # True
            return -9
        return 0

    # wait_end_cashout_result(self, timeout_sec)
    # Input:
    #    timeout_sec: await how many second to get the result. 
    #                 if not given, wait util getting result
    # return: json object
    # { 
    #   "result_code": int - 1=still in progress (nothing changed)
    #                        0=got result 
    #                       -3=no prior request (nothing changed)
    #                       -4=disorder error (should call wait_req_cashout_result!!!)
    #   ## the below is valid only if result_code==0;
    #   "http_status_code": int - the status code returned from HTTP server. for reference only
    #                             (for non-2xx: do internal retry, won't be seen outside)
    #   "status": str - "0-OK" 表示成功.
    #                   "1-NO RECORD" 表示無對應入金紀錄, 可視為邏輯錯誤, 應結束流程,
    #                   "6-BAD DATA/FORMAT" (邏輯錯誤, 應結束流程),
    #                   "7-OUT OF SERVICE" (internal retry, won't be seen outside),
    #                   "9-OTHER ERROR" (internal retry, won't be seen outside)
    #   "currency": str - (for reference only)
    #   "value": float - the money; (for reference only)
    #   "TXID": str - the unique Id of the transaction; (for reference only)
    #   "dateTime": str - 事件/Complete 時間. 格式: "<YYYY>-<MM>-<DD>T<HH>:<mm>:<SS>[.<sss>]Z"
    # }
    # Remark:
    #   - if "result_code"<>1, the cashin transaction is always ended
    def wait_end_cashout_result(self, timeout_sec:float|None = None) -> dict:
        if self.__co_TXID == '':
            return {"result_code": -4}

        if not self.__co_b_req_idle.is_set():
            if not self.__co_b_req_idle.wait(timeout_sec):
                return {"result_code": 1}
        if self.__co_thr is not None:
            try:
                self.__co_thr.join()
            except:
                print('join thread fail!')
                pass
            self.__co_thr = None

        if self.__co_json_data is None:
            return {"result_code": -3}
        
        self.__co_TXID = ''
        self.__co_value = 0.0
        json_data = self.__co_json_data
        self.__co_json_data = None
        self.co_event.clear()
        return json_data

#
# This is for testing only
# Return '' or <token> string
#
def __load_token() -> str:
    token = ''
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
    api_base_url = 'https://api.n1s168.com'
    webapi = n1s168_webapi(api_base_url)
    token:str = ''

    while True:
        print('\nInput a number with [enter]:')
        print('<1> get token and generate to ./token.txt')
        print('<2> load token from ./token.txt')
        print('<3> do cash in - phase 1')
        print('<4> do cash in - phase 2')
        print('<5> do cash out - phase 1')
        print('<6> do cash out - phase 2')
        print('<q> quit')

        func = input().strip()
        if func == '':
            continue
        
        if func[0] == '1':
            print('Get API token example')
            print('Input parameters (may input partial)')
            print('<account> <password>:', end='')
            argv = input().strip().split()
            argv_len = len(argv)
            
            account = argv[0] if argv_len > 0 else 'ITgame01'
            password = argv[1] if argv_len > 1 else 'ITgame01'
            print('account:', account)
            print('pasword:', password)
            
            json_data = webapi.fetch_token(account, password)
            print('Return:')
            print(json_data)
            if json_data['result_code'] == 0:
                print('0=success')
            elif json_data['result_code'] == -1:
                print('-1=API request error')
            elif json_data['result_code'] == -2:
                print('-2=http status code is not 2xx')
            elif json_data['result_code'] == -3:
                print('-3=status field is False')
            else:
                print('unknown', json_data['result_code'])

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

                    webapi.set_token(json_data['token'])
                    print('done')
                except:
                    print('write failed!')
                    os._exit(1)
       
        elif func[0] == '2':
            print('Load token from file ./token.txt')
            token:str = __load_token()
            webapi.set_token(token)
            print('token loaded.' if token != '' else 'token was reset.')
        
        elif func[0] == '3':
            print('Do cash-in - phase 1')
            print('Input parameter (may input nothing for 5.0 dollars by default)')
            print('<dollar(float)>:', end='')
            argv = input().strip().split()
            argv_len = len(argv)
            value = float(argv[0]) if argv_len > 0 else 5.0
            print('money:', value)

            ######################################
            # PHASE 1
            ######################################
            # raise request. will run in a background thread.
            ret = webapi.req_cashin(value)
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
                    json_data = webapi.wait_req_cashin_result(timeout_sec=1.0)
                    if json_data['result_code'] != 1:
                        break
                    print(".")
                print(json_data)    # for debug
                if json_data['result_code'] == 0:
                    print('0=got result (http status ', json_data['http_status_code'],')',sep='')
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

                # if cannot go further, end
                if json_data["result_code"] != 0 or json_data["status"][0] != '0':
                    print('Cash in transaction terminated.')
                else:
                    print('May go to cash in phase 2')
 
        elif func[0] == '4':
            print('Do cash-in - phase 2')

            ######################################
            # PHASE 2
            ######################################
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
                    json_data = webapi.wait_end_cashin_result(timeout_sec=1.0)
                    if json_data['result_code'] != 1:
                        break
                    print(".")
                print(json_data)    # for debug
                if json_data['result_code'] == 0:
                    print('0=got result (http status ', json_data['http_status_code'],')',sep='')
                elif json_data['result_code'] == -3:
                    print('-3=no prior request')
                elif json_data['result_code'] == -4:
                    print('-4=disorder error')
                else:
                    print('unknown', json_data['result_code'])
            print('Cash in transaction ended.')
      
        elif func[0] == '5':
            print('Do cash-out - phase 1')

            ######################################
            # PHASE 1
            ######################################
            # raise request. will run in a background thread.
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
                    json_data = webapi.wait_req_cashout_result(timeout_sec=1.0)
                    if json_data['result_code'] != 1:
                        break
                    print(".")
                print(json_data)    # for debug
                if json_data['result_code'] == 0:
                    print('0=got result (http status ', json_data['http_status_code'],')',sep='')
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

                # if cannot go further, end
                if json_data["result_code"] != 0 or json_data["status"][0] != '0':
                    print('Cash out transaction terminated.')
                else:
                    print('May go to cash out phase 2')
 
        elif func[0] == '6':
            print('Do cash-out - phase 2')

            ######################################
            # PHASE 2
            ######################################
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
                    json_data = webapi.wait_end_cashout_result(timeout_sec=1.0)
                    if json_data['result_code'] != 1:
                        break
                    print(".")
                print(json_data)    # for debug
                if json_data['result_code'] == 0:
                    print('0=got result (http status ', json_data['http_status_code'],')',sep='')
                elif json_data['result_code'] == -3:
                    print('-3=no prior request')
                elif json_data['result_code'] == -4:
                    print('-4=disorder error')
                else:
                    print('unknown', json_data['result_code'])
            print('Cash out transaction ended.')
      
        elif func[0] in ['q', 'Q']:
            break
      
    print('Done')
