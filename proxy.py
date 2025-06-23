import json
import os
import traceback
import requests

from config import Config
from log_tool import Logger


class HttpClient:
    def __init__(self):
        host = os.environ.get('edgeServerHost')
        if host:
            self.host = host
        else:
            self.host = Config.edge_server_host
        Logger.info(f'edge server host:{self.host}')
        self.timeout = Config.timeout
        self.success_code = 20000

    def get(self, uri, headers=None, params=None):
        return self._run('get', self.host + uri, headers, params)

    def post(self, uri, headers=None, data=None):
        return self._run('post_json', self.host + uri, headers=headers, params=None, data=data)

    def delete(self, uri, headers=None, data=None):
        return self._run('delete_json', self.host + uri, headers=headers, params=None, data=data)

    def _run(self, method, url, headers=None, params=None, data=None):
        try:
            print(f'请求URL:{url}')
            print(f'请求头:{headers and json.dumps(headers)}')
            print(f'查询字符串:{params and json.dumps(params)}')
            print(f'请求体:{data and json.dumps(data)}')
            if method == 'get':
                response = requests.get(url, params, headers=headers, timeout=self.timeout)
            elif method == 'post_form':
                response = requests.post(url, data=data, headers=headers, timeout=self.timeout)
            elif method == 'post_json':
                response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            elif method == 'delete_json':
                response = requests.delete(url, json=data, headers=headers, timeout=self.timeout)
            else:
                return 'method not support', False
        except Exception as e:
            print(traceback.format_exc())
            return '请求异常', False
        else:
            print(f'响应:{response.text}')
            if response.status_code != 200:
                return response.text, False
            result_data = response.json()
            if result_data['code'] == self.success_code:
                return result_data.get('response'), True
            return result_data.get('message'), False


http_client = HttpClient()
