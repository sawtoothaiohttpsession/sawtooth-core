# Copyright 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------
  
import pytest
import logging
import json
import urllib.request
import urllib.error
from urllib.request import urlopen
from urllib.error import HTTPError
from urllib.error import URLError
import base64
import argparse
import cbor
import subprocess
import shlex
import requests
import hashlib
import os
import time
import aiohttp

    
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
    
WAIT = 300


class RestClient:
    def _make_http_address(self,node_number):
        node = node_number.replace('tcp' , 'http')
        node_number = node.replace('8800' , '8008')
        return node_number
    
    def _get_client_address(self): 
        command = "hostname -I | awk '{print $1}'"
        node_ip = subprocess.check_output(command , shell=True).decode().strip().replace("'", '"')
        return 'http://' + node_ip + ':8008'
    
    def query_rest_api(self,suffix='', data=None, headers=None):
        if headers is None:
            headers = {}
        url = self._get_client_address() + suffix
        return self.submit_request(urllib.request.Request(url, data, headers))
    
    def submit_request(self,request):
        response = urllib.request.urlopen(request).read().decode('utf-8')
        return json.loads(response)
    
    def post_batch(self,batch, headers="None"):
        if headers=="True":
            headers = {'Content-Type': 'application/json'}  
        else:
            headers = {'Content-Type': 'application/octet-stream'}
        
        response = self.query_rest_api(
            '/batches', data=batch, headers=headers)
        
        response = self.submit_request('{}&wait={}'.format(response['link'], WAIT))
        return response
            
    def get_blocks(self,head_id=None , id=None , start=None , limit=None , reverse=None):  
        if all(v is not None for v in [head_id , id]):
            response = self.query_rest_api('/blocks?head={}&id={}'.format(head_id , id))
            return response
        if all(v is not None for v in [start , limit]):
            response = self.query_rest_api('/blocks?start={}&limit={}'.format(start , limit))
            return response
        if limit is not None:
            response = self.query_rest_api('/blocks?limit=%s'% limit)
            return response 
        if start is not None:
            response = self.query_rest_api('/blocks?start=%s'% start)
            return response 
        if head_id is not None:
            response = self.query_rest_api('/blocks?head=%s'% head_id)
            return response 
        if id is not None:
            response = self.query_rest_api('/blocks?id=%s'% id)
            return response
        if reverse:
            response = self.query_rest_api('/blocks?reverse')
            return response
        else:
            response = self.query_rest_api('/blocks')
            return response
    
    
    def get_batches(self,head_id=None , id=None , start=None , limit=None, reverse=None):  
        if all(v is not None for v in [head_id , id]):
            response = self.query_rest_api('/batches?head={}&id={}'.format(head_id , id))
            return response
        if all(v is not None for v in [start , limit]):
            response = self.query_rest_api('/batches?start={}&limit={}'.format(start , limit))
            return response
        if limit is not None:
            response = self.query_rest_api('/batches?limit=%s'% limit)
            return response 
        if start is not None:
            response = self.query_rest_api('/batches?start=%s'% start)
            return response 
        if head_id is not None:
            response = self.query_rest_api('/batches?head=%s'% head_id)
            return response 
        if id is not None:
            response = self.query_rest_api('/batches?id=%s'% id)
            return response
        if reverse:
            response = self.query_rest_api('/batches?reverse')
            return response
        else:
            response = self.query_rest_api('/batches')
            return response
    
    def get_batch_id(self,batch_id):
        response = self.query_rest_api('/batches/%s' % batch_id)
        return response
    
    def get_block_id(self,block_id):
        response = self.query_rest_api('/blocks/%s' % block_id)
        return response
    
    def get_transaction_id(self,transaction_id):
        response = self.query_rest_api('/transactions/%s' % transaction_id)
        return response
    
    def get_peers(self):
        response = self.query_rest_api('/peers')
        return response
    
    def get_transactions(self,head_id=None , id=None , start=None , limit=None , reverse=None):
        if all(v is not None for v in [head_id , id]):
            response = self.query_rest_api('/transactions?head={}&id={}'.format(head_id , id))
            return response
        if all(v is not None for v in [start , limit]):
            response = self.query_rest_api('/transactions?start={}&limit={}'.format(start , limit))
            return response
        if limit is not None:
            response = self.query_rest_api('/transactions?limit=%s'% limit)
            return response 
        if start is not None:
            response = self.query_rest_api('/transactions?start=%s'% start)
            return response 
        if head_id is not None:
            response = self.query_rest_api('/transactions?head=%s'% head_id)
            return response 
        if id is not None:
            response = self.query_rest_api('/transactions?id=%s'% id)
            return response
        if reverse:
            response = self.query_rest_api('/transactions?reverse')
            return response
        else:
            response = self.query_rest_api('/transactions')
            return response
    
    def get_state_list(self,head_id=None , address=None , start=None , limit=None , reverse=None):
        if all(v is not None for v in [head_id , address]):
            response = self.query_rest_api('/state?head={}&address={}'.format(head_id , address))
            return response
        if all(v is not None for v in [start , limit]):
            response = self.query_rest_api('/state?start={}&limit={}'.format(start , limit))
            return response
        if limit is not None:
            response = self.query_rest_api('/state?limit=%s'% limit)
            return response 
        if start is not None:
            response = self.query_rest_api('/state?start=%s'% start)
            return response 
        if head_id is not None:
            response = self.query_rest_api('/state?head=%s'% head_id)
            return response 
        if address is not None:
            response = self.query_rest_api('/state?address=%s'% address)
            return response
        if reverse:
            response = self.query_rest_api('/state?reverse')
            return response
        else:
            response = self.query_rest_api('/state')
            return response
    
    def get_state_address(self,address):
        response = self.query_rest_api('/state/%s' % address)
        return response
    
    
    def get_batch_statuses(self,batch_ids=None, wait=None):
        try:
            batches = ",".join(batch_ids)
        except:
            batches = None
        
        if batches:
            if wait == 'default':
                response = self.query_rest_api('/batch_statuses?wait&id={}'.format(batches))
                return response
            elif wait:
                response = self.query_rest_api('/batch_statuses?id={}&wait={}'.format(batches,wait))
                return response
            else:
                response = self.query_rest_api('/batch_statuses?id=%s' % batches)
                return response       
        else:
            response = self.query_rest_api('/batch_statuses')
            return response
    
    def get_reciepts(self,reciept_id):
        response = self.query_rest_api('/receipts?id=%s' % reciept_id)
        return response
    
    def post_receipts(self,receipts):
        headers = {'Content-Type': 'application/json'}
        response = self.query_rest_api('/receipts', data=receipts, headers=headers)
        return response
    
    def _get_peers_list(rest_client, fmt='json'):
        cmd_output = _run_peer_command(
            'sawtooth peer list --url {} --format {}'.format(
                rest_client,
                fmt))
    
        if fmt == 'json':
            parsed = json.loads(cmd_output)
    
        elif fmt == 'csv':
            parsed = cmd_output.split(',')
    
        return set(parsed)
    
    def _run_peer_command(command):
        return subprocess.check_output(
            shlex.split(command)
        ).decode().strip().replace("'", '"')
    
    def _send_cmd(cmd_str):
        LOGGER.info('Sending %s', cmd_str)
    
        subprocess.run(
            shlex.split(cmd_str),
            check=True)
