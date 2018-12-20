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
import aiohttp
import asyncio
import datetime
import random
import time

from google.protobuf.json_format import MessageToDict

from sawtooth_rest_api.protobuf.batch_pb2 import BatchList

from utils import post_batch, get_state_list , get_blocks , get_transactions, \
                  get_batches , get_state_address, check_for_consensus,\
                  _get_node_list, _get_node_chains, post_batch_no_endpoint,\
                  get_reciepts, _get_client_address, state_count, get_batch_id, get_transaction_id
     
from utils import _get_client_address

from payload import get_signer, create_intkey_transaction, create_batch,\
                    create_intkey_same_transaction,  \
                    create_intkey_transaction_dep, random_word_list, create_invalid_Address_intkey_dep_txn

from base import RestApiBaseTest

from fixtures import setup_empty_trxs_batch, setup_invalid_txns,setup_invalid_txns_min,\
                     setup_invalid_txns_max, setup_valinv_txns, setup_invval_txns, \
                     setup_same_txns, setup_valid_txns, setup_invalid_txns_fn,\
                     setup_invalid_invaddr, post_batch_txn, validate_Response_Status_txn
                  
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

WAIT=300

BLOCK_TO_CHECK_CONSENSUS = 1

pytestmark = [pytest.mark.dependent,pytest.mark.sixth]

async def async_fetch_url(url, session,params=None):
    try:
        async with session.get(url) as response:
            return await response.json()
    except aiohttp.client_exceptions.ClientResponseError as error:
        LOGGER.info(error)

async def async_post_batch(url, session, data, params=None,headers=None):
    if headers:
        headers=headers
    else:
        headers = {'Content-Type': 'application/octet-stream'}
    try:
        async with session.post(url,data=data,headers=headers) as response:
            data = await response.json()
            if 'link' in data:
                link = data['link']
                return await async_fetch_url('{}&wait={}'.format(link, WAIT),session)
            else:
                return data
    except aiohttp.client_exceptions.ClientResponseError as error:
        LOGGER.info(error)
          

#testing the Transaction dependencies
class TestPostTansactionDependencies(RestApiBaseTest):
    
    async def test_set_inc_txn_dep(self, setup):
        """"1. Create first Transaction for set                                                                                                                                                                                                                      
            2. Create second Transaction for increment with first Transaction as dependecies                           
            3. Create Batch                                                                                                                                   
            4. Call POST /batches "
            Verify the transactions
        """
        LOGGER.info('Starting test for batch post')
    
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks=[]

        name = random.choice("abcdefghijklmnopqrstuv")
    
        LOGGER.info("Creating intkey transactions with set operations")

        txns = [
            create_intkey_transaction_dep("set", [] , name, 50, signer),]
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)

            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
            
        
        LOGGER.info("Creating intkey transactions with inc operations with dependent transactions as first transaction")
        trxn_ids = expected_trxn_ids
        txns.append(create_intkey_transaction_dep("inc", trxn_ids , name, 20, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
           
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)        

        LOGGER.info("Creating batches for transactions 1trn/batch")
     
        batches = [create_batch([txn], signer) for txn in txns]
     
        for batch in batches:
            data = MessageToDict(
                    batch,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
      
            batch_id = data['header_signature']
            expected_batch_ids.append(batch_id)
       
        post_batch_list = [BatchList(batches=[batch]).SerializeToString() for batch in batches]
     
        LOGGER.info("Submitting batches to the handlers")
      
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks.append(task)
                responses = await asyncio.gather(*tasks)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
        
        LOGGER.info("Verifying the responses status")
        
        for response in responses:
            batch_id = response['data'][0]['id']

            if response['data'][0]['status'] == 'COMMITTED':
                LOGGER.info('Batch with id {} is successfully got committed'.format(batch_id))
                        
            elif response['data'][0]['status'] == 'INVALID':
                LOGGER.info('Batch with id {} is not committed. Status is INVALID'.format(batch_id))
 
            elif response['data'][0]['status'] == 'UNKNOWN':
                LOGGER.info('Batch with id {} is not committed. Status is UNKNOWN'.format(batch_id))
        
        LOGGER.info("Verifying the txn details listed under the dependencies")
        trxn_ids = list(set(expected_trxn_ids))
        
        for txn_id in trxn_ids:
            txn_details = get_transaction_id(txn_id)
            if (self.assert_check_txn_dependency(txn_details, trxn_ids)):
                LOGGER.info("Successfully got the dependencies for transaction id "+ txn_id)
            else:
                LOGGER.info("The dependencies for transaction id is blank"+ txn_id)
                     
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
    
    async def test_rest_api_double_dep_txns(self, setup):
        """1. Create first Transaction for set                                                                                                                                                                                                                      
        2. Create second Transaction for increment with first Transaction as dependecies                                                             
        3. Create third Transaction for decrement with first and second Transaction as dependecies                                                            
        4. Create Batch                                                                                                                                   
        5. Call POST /batches
        Verify the transactions
        """
        LOGGER.info('Starting test for batch post')    
            
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks=[]
        name = random.choice("abcdefghijklmnopqrstuv")   
    
        LOGGER.info("Creating intkey transactions with set operations")

        txns = [
            create_intkey_transaction_dep("set", [] , name, 50, signer),]
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)

            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
            
        
        LOGGER.info("Creating intkey transactions with inc operations with dependent transactions as first transaction")
        trxn_ids = expected_trxn_ids
        txns.append(create_intkey_transaction_dep("inc", trxn_ids , name, 20, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
           
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)  
                  
        LOGGER.info("Creating intkey transactions with inc operations with dependent transactions as first and second transaction")
        trxn_ids = expected_trxn_ids
        txns.append(create_intkey_transaction_dep("dec", trxn_ids , name, 50, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
           
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id) 

        LOGGER.info("Creating batches for transactions 1trn/batch")
     
        batches = [create_batch([txn], signer) for txn in txns]
     
        for batch in batches:
            data = MessageToDict(
                    batch,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
      
            batch_id = data['header_signature']
            expected_batch_ids.append(batch_id)
       
        post_batch_list = [BatchList(batches=[batch]).SerializeToString() for batch in batches]
     
        LOGGER.info("Submitting batches to the handlers")
      
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks.append(task)
                responses = await asyncio.gather(*tasks)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
        
        LOGGER.info("Verifying the responses status")
        
        for response in responses:
            batch_id = response['data'][0]['id']

            if response['data'][0]['status'] == 'COMMITTED':
                LOGGER.info('Batch with id {} is successfully got committed'.format(batch_id))
                        
            elif response['data'][0]['status'] == 'INVALID':
                LOGGER.info('Batch with id {} is not committed. Status is INVALID'.format(batch_id))
 
            elif response['data'][0]['status'] == 'UNKNOWN':
                LOGGER.info('Batch with id {} is not committed. Status is UNKNOWN'.format(batch_id))
        
        LOGGER.info("Verifying the txn details listed under the dependencies")
        trxn_ids = list(set(expected_trxn_ids))
        
        for txn_id in trxn_ids:
            txn_details = get_transaction_id(txn_id)
            if (self.assert_check_txn_dependency(txn_details, trxn_ids)):
                LOGGER.info("Successfully got the dependencies for transaction id "+ txn_id)
            else:
                LOGGER.info("The dependencies for transaction id is blank"+ txn_id)
                     
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
       
    async def test_single_set_dep_txns(self, setup):
        """"1. Create first Transaction for set                                                                                                                                                                                                                      
            2. Create second Transaction for increment with first Transaction as dependecies                           
            3. Create Batch                                                                                                                                   
            4. Call POST /batches "
            Verify the transactions
        """
        LOGGER.info('Starting test for batch post')
     
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks=[]
        t = datetime.datetime.now()
        date = t.strftime('%H%M%S')
        words = random_word_list(100)
        name=random.choice(words) 
        
        #name=random.choice('123456734558909877') 
         
     
        LOGGER.info("Creating intkey transactions with set operations")
 
        txns = [
            create_intkey_transaction_dep("set", [] , name, 50, signer),]
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
 
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
             
         
        LOGGER.info("Creating intkey transactions with inc operations with dependent transactions as first transaction")
        trxn_ids = expected_trxn_ids
        words = random_word_list(100)
        name=random.choice(words) 
        #name=random.choice('123456734558909877') 
        txns.append(create_intkey_transaction_dep("set",trxn_ids, name, 20, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
            
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)        
 
        LOGGER.info("Creating batches for transactions 1trn/batch")
      
        batches = [create_batch([txn], signer) for txn in txns]
      
        for batch in batches:
            data = MessageToDict(
                    batch,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
       
            batch_id = data['header_signature']
            expected_batch_ids.append(batch_id)
        
        post_batch_list = [BatchList(batches=[batch]).SerializeToString() for batch in batches]
      
        LOGGER.info("Submitting batches to the handlers")
       
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks.append(task)
                responses = await asyncio.gather(*tasks)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
         
        LOGGER.info("Verifying the responses status")
         
        for response in responses:
            batch_id = response['data'][0]['id']
 
            if response['data'][0]['status'] == 'COMMITTED':
                assert response['data'][0]['status'] == 'COMMITTED'
                 
                LOGGER.info('Batch with id {} is successfully got committed'.format(batch_id))
                         
            elif response['data'][0]['status'] == 'INVALID':
                assert response['data'][0]['status'] == 'INVALID'
                 
                LOGGER.info('Batch with id {} is not committed. Status is INVALID'.format(batch_id))
  
            elif response['data'][0]['status'] == 'UNKNOWN':
                assert response['data'][0]['status'] == 'UNKNOWN'
                LOGGER.info('Batch with id {} is not committed. Status is UNKNOWN'.format(batch_id))
         
        LOGGER.info("Verifying the txn details listed under the dependencies")
        trxn_ids = list(set(expected_trxn_ids))
         
        for txn_id in trxn_ids:
            txn_details = get_transaction_id(txn_id)
            if (self.assert_check_txn_dependency(txn_details, trxn_ids)):
                LOGGER.info("Successfully got the dependencies for transaction id "+ txn_id)
            else:
                LOGGER.info("The dependencies for transaction id is blank"+ txn_id)
                      
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
        
    async def test_rest_api_single_set_dec_txns(self, setup):
        """"1. Create first Transaction for set                                                                                                                                                                                                                      
            2. Create second Transaction for increment with first Transaction as dependecies                           
            3. Create Batch                                                                                                                                   
            4. Call POST /batches "
            Verify the transactions
        """
        LOGGER.info('Starting test for batch post')
    
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks=[]
        t = datetime.datetime.now()
        date = t.strftime('%H%M%S')
        words = random_word_list(100)
        name=random.choice(words) 
       
        #name=random.choice('123456734558909877yuyiipp879798788') 
        
    
        LOGGER.info("Creating intkey transactions with set operations")

        txns = [
            create_intkey_transaction_dep("set", [] , name, 50, signer),]
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)

            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
            
        
        LOGGER.info("Creating intkey transactions with inc operations with dependent transactions as first transaction")
        trxn_ids = expected_trxn_ids
        #name=random.choice('123456734558909877') 
        txns.append(create_intkey_transaction_dep("dec",trxn_ids , name, 60, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
           
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)        

        LOGGER.info("Creating batches for transactions 1trn/batch")
     
        batches = [create_batch([txn], signer) for txn in txns]
     
        for batch in batches:
            data = MessageToDict(
                    batch,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
      
            batch_id = data['header_signature']
            expected_batch_ids.append(batch_id)
       
        post_batch_list = [BatchList(batches=[batch]).SerializeToString() for batch in batches]
     
        LOGGER.info("Submitting batches to the handlers")
      
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks.append(task)
                responses = await asyncio.gather(*tasks)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
        
        LOGGER.info("Verifying the responses status")
        
        for response in responses:
            #batch_id = response['data'][0]['id']

            if response['data'][0]['status'] == 'COMMITTED':
                assert response['data'][0]['status'] == 'COMMITTED'
                
                LOGGER.info('Batch with id {} is successfully got committed'.format(batch_id))
                        
            elif response['data'][0]['status'] == 'INVALID':
                assert response['data'][0]['status'] == 'INVALID'
                
                LOGGER.info('Batch with id {} is not committed. Status is INVALID'.format(batch_id))
 
            elif response['data'][0]['status'] == 'UNKNOWN':
                assert response['data'][0]['status'] == 'UNKNOWN'
                LOGGER.info('Batch with id {} is not committed. Status is UNKNOWN'.format(batch_id))
        LOGGER.info("Verifying the txn details listed under the dependencies")
        trxn_ids = list(set(expected_trxn_ids))
        
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
    
    async def test_rest_api_set_inc_inc_Txns_Dep(self, setup):
        """1. Create first Transaction for set                                                                                                                                                                                                                      
        2. Create second Transaction for increment with first Transaction as dependecies
        3. Create third Transaction for increment with first and second Transaction as dependecies                                                                                                                
        3. Create Batch                                                                                                                                   
        4. Call POST /batches
        Verify the transactions
        """
        LOGGER.info('Starting test for batch post')
    
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks=[]
        name = random.choice("abcdefghijklmnopqrstuv")
    
        LOGGER.info("Creating intkey transactions with set operations")

        txns = [
            create_intkey_transaction_dep("set", [] , name, 50, signer),]
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)

            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
            
        
        LOGGER.info("Creating intkey transactions with inc operations with dependent transactions as first transaction")
        trxn_ids = expected_trxn_ids
        txns.append(create_intkey_transaction_dep("inc", trxn_ids , name, 20, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
           
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)     
            
        LOGGER.info("Creating intkey transactions with inc operations with dependent transactions as second transaction")
        trxn_ids = list(set(expected_trxn_ids))
        txns.append(create_intkey_transaction_dep("inc", trxn_ids , name, 50, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
           
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)    

        LOGGER.info("Creating batches for transactions 1trn/batch")
     
        batches = [create_batch([txn], signer) for txn in txns]
     
        for batch in batches:
            data = MessageToDict(
                    batch,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
      
            batch_id = data['header_signature']
            expected_batch_ids.append(batch_id)
       
        post_batch_list = [BatchList(batches=[batch]).SerializeToString() for batch in batches]
     
        LOGGER.info("Submitting batches to the handlers")
      
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks.append(task)
                responses = await asyncio.gather(*tasks)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
        
        LOGGER.info("Verifying the responses status")
        
        for response in responses:
            batch_id = response['data'][0]['id']

            if response['data'][0]['status'] == 'COMMITTED':
                LOGGER.info('Batch with id {} is successfully got committed'.format(batch_id))
                        
            elif response['data'][0]['status'] == 'INVALID':
                LOGGER.info('Batch with id {} is not committed. Status is INVALID'.format(batch_id))
 
            elif response['data'][0]['status'] == 'UNKNOWN':
                LOGGER.info('Batch with id {} is not committed. Status is UNKNOWN'.format(batch_id))
        
        LOGGER.info("Verifying the txn details listed under the dependencies")
        trxn_ids = list(set(expected_trxn_ids))
        
        for txn_id in trxn_ids:
            txn_details = get_transaction_id(txn_id)
            if (self.assert_check_txn_dependency(txn_details, trxn_ids)):
                LOGGER.info("Successfully got the dependencies for transaction id "+ txn_id)
            else:
                LOGGER.info("The dependencies for transaction id is blank"+ txn_id)
                     
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
        
    async def test_rest_api_single_set_dec_same_txns(self, setup):
        """"1. Create first Transaction for set                                                                                                                                                                                                                      
            2. Create second Transaction for increment with first Transaction as dependecies                           
            3. Create Batch                                                                                                                                   
            4. Call POST /batches "
            Verify the transactions
        """
        LOGGER.info('Starting test for batch post')
    
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks=[]
        t = datetime.datetime.now()
        date = t.strftime('%H%M%S')
        words = random_word_list(100)
        name=random.choice(words) 
       
        #name=random.choice('123456734558909877yuyiipp879798788') 
        
    
        LOGGER.info("Creating intkey transactions with set operations")

        txns = [
            create_intkey_transaction_dep("set", [] , name, 50, signer),]
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)

            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
            
        
        LOGGER.info("Creating intkey transactions with inc operations with dependent transactions as first transaction")
        trxn_ids = expected_trxn_ids
        #name=random.choice('123456734558909877') 
        txns.append(create_intkey_transaction_dep("dec",trxn_ids , name, 50, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
           
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)        

        LOGGER.info("Creating batches for transactions 1trn/batch")
     
        batches = [create_batch([txn], signer) for txn in txns]
     
        for batch in batches:
            data = MessageToDict(
                    batch,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
      
            batch_id = data['header_signature']
            expected_batch_ids.append(batch_id)
       
        post_batch_list = [BatchList(batches=[batch]).SerializeToString() for batch in batches]
     
        LOGGER.info("Submitting batches to the handlers")
      
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks.append(task)
                responses = await asyncio.gather(*tasks)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
        
        LOGGER.info("Verifying the responses status")
        
        for response in responses:
            #batch_id = response['data'][0]['id']

            if response['data'][0]['status'] == 'COMMITTED':
                assert response['data'][0]['status'] == 'COMMITTED'
                
                LOGGER.info('Batch with id {} is successfully got committed'.format(batch_id))
                        
            elif response['data'][0]['status'] == 'INVALID':
                assert response['data'][0]['status'] == 'INVALID'
                
                LOGGER.info('Batch with id {} is not committed. Status is INVALID'.format(batch_id))
 
            elif response['data'][0]['status'] == 'UNKNOWN':
                assert response['data'][0]['status'] == 'UNKNOWN'
                LOGGER.info('Batch with id {} is not committed. Status is UNKNOWN'.format(batch_id))
        LOGGER.info("Verifying the txn details listed under the dependencies")
        trxn_ids = list(set(expected_trxn_ids))
        
        '''
        for txn_id in trxn_ids:
            #txn_details = get_transaction_id(txn_id)
            if (self.assert_check_txn_dependency(txn_details, trxn_ids)):
                LOGGER.info("Successfully got the dependencies for transaction id "+ txn_id)
            else:
                LOGGER.info("The dependencies for transaction id is blank"+ txn_id)
        '''       
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
        
    async def test_rest_api_single_set_dec_invalid_txns_id(self, setup):
        """"1. Create first Transaction for set                                                                                                                                                                                                                      
            2. Create second Transaction for increment with first Transaction as dependecies                           
            3. Create Batch                                                                                                                                   
            4. Call POST /batches "
            Verify the transactions
        """
        LOGGER.info('Starting test for batch post')
    
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks=[]
        t = datetime.datetime.now()
        date = t.strftime('%H%M%S')
        words = random_word_list(100)
        name=random.choice(words) 
       
        #name=random.choice('123456734558909877yuyiipp879798788') 
        
    
        LOGGER.info("Creating intkey transactions with set operations")

        txns = [
            create_intkey_transaction_dep("set", [] , name, 50, signer),]
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)

            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
            
        
        LOGGER.info("Creating intkey transactions with inc operations with dependent transactions as first transaction")
        trxn_ids = expected_trxn_ids
        #name=random.choice('123456734558909877') 
        txns.append(create_intkey_transaction_dep("dec",[u'bbbbbb'] , name, 50, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
           
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)        

        LOGGER.info("Creating batches for transactions 1trn/batch")
     
        batches = [create_batch([txn], signer) for txn in txns]
     
        for batch in batches:
            data = MessageToDict(
                    batch,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
      
            batch_id = data['header_signature']
            expected_batch_ids.append(batch_id)
       
        post_batch_list = [BatchList(batches=[batch]).SerializeToString() for batch in batches]
     
        LOGGER.info("Submitting batches to the handlers")
      
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks.append(task)
                responses = await asyncio.gather(*tasks)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
        
        LOGGER.info("Verifying the responses status")
        
        for response in responses:
            #batch_id = response['data'][0]['id']

            if response['data'][0]['status'] == 'COMMITTED':
                assert response['data'][0]['status'] == 'COMMITTED'
                
                LOGGER.info('Batch with id {} is successfully got committed'.format(batch_id))
                        
            elif response['data'][0]['status'] == 'INVALID':
                assert response['data'][0]['status'] == 'INVALID'
                
                LOGGER.info('Batch with id {} is not committed. Status is INVALID'.format(batch_id))
 
            elif response['data'][0]['status'] == 'UNKNOWN':
                assert response['data'][0]['status'] == 'UNKNOWN'
                LOGGER.info('Batch with id {} is not committed. Status is UNKNOWN'.format(batch_id))
        LOGGER.info("Verifying the txn details listed under the dependencies")
        trxn_ids = list(set(expected_trxn_ids))
        '''
        for txn_id in trxn_ids:
            #txn_details = get_transaction_id(txn_id)
            if (self.assert_check_txn_dependency(txn_details, trxn_ids)):
                LOGGER.info("Successfully got the dependencies for transaction id "+ txn_id)
            else:
                LOGGER.info("The dependencies for transaction id is blank"+ txn_id)
        '''       
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
        
    async def test_single_set_dep_reverse(self, setup):
         """"1. Create first Transaction for set                                                                                                                                                                                                                      
             2. Create second Transaction for increment with first Transaction as dependecies                           
             3. Create Batch                                                                                                                                   
             4. Call POST /batches "
             Verify the transactions
         """
         LOGGER.info('Starting test for batch post')
      
         signer = get_signer()
         expected_trxn_ids  = []
         expected_batch_ids = []
         address = _get_client_address()
         url='{}/batches'.format(address)
         tasks=[]
         t = datetime.datetime.now()
         date = t.strftime('%H%M%S')
         words = random_word_list(100)
         name=random.choice(words) 
         
         #name=random.choice('123456734558909877') 
          
      
         LOGGER.info("Creating intkey transactions with set operations")
  
         txns = [
             create_intkey_transaction_dep("set", [] , name, 5, signer),]
         for txn in txns:
             data = MessageToDict(
                     txn,
                     including_default_value_fields=True,
                     preserving_proto_field_name=True)
  
             trxn_id = data['header_signature']
             expected_trxn_ids.append(trxn_id)
              
          
         LOGGER.info("Creating intkey transactions with inc operations with dependent transactions as first transaction")
         trxn_ids = expected_trxn_ids
         words = random_word_list(100)
         name=random.choice(words) 
         #name=random.choice('123456734558909877') 
         txns.append(create_intkey_transaction_dep("set",trxn_ids, name, 2, signer))  
         for txn in txns:
             data = MessageToDict(
                     txn,
                     including_default_value_fields=True,
                     preserving_proto_field_name=True)
             
             trxn_id = data['header_signature']
             expected_trxn_ids.append(trxn_id)        
  
         LOGGER.info("Creating batches for transactions 1trn/batch")
       
         batches = [create_batch([txn], signer) for txn in txns[::-1]]
       
         for batch in batches:
             data = MessageToDict(
                     batch,
                     including_default_value_fields=True,
                     preserving_proto_field_name=True)
        
             batch_id = data['header_signature']
             expected_batch_ids.append(batch_id)
         
         post_batch_list = [BatchList(batches=[batch]).SerializeToString() for batch in batches]
       
         LOGGER.info("Submitting batches to the handlers")
        
         try:
             async with aiohttp.ClientSession() as session: 
                 for batch in post_batch_list:
                     task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                     response = await asyncio.gather(task)
                     #print(response) 
                 responses = await asyncio.gather(*tasks)
                     
         except aiohttp.client_exceptions.ClientResponseError as error:
             LOGGER.info("Rest Api is Unreachable")
          
         LOGGER.info("Verifying the responses status")
          
         for response in responses:
             batch_id = response['data'][0]['id']
  
             if response['data'][0]['status'] == 'COMMITTED':
                 assert response['data'][0]['status'] == 'COMMITTED'
                  
                 LOGGER.info('Batch with id {} is successfully got committed'.format(batch_id))
                          
             elif response['data'][0]['status'] == 'INVALID':
                 assert response['data'][0]['status'] == 'INVALID'
                  
                 LOGGER.info('Batch with id {} is not committed. Status is INVALID'.format(batch_id))
   
             elif response['data'][0]['status'] == 'UNKNOWN':
                 assert response['data'][0]['status'] == 'UNKNOWN'
                 LOGGER.info('Batch with id {} is not committed. Status is UNKNOWN'.format(batch_id))
          
         LOGGER.info("Verifying the txn details listed under the dependencies")
         trxn_ids = list(set(expected_trxn_ids))
         
         node_list = _get_node_list()
         chains = _get_node_chains(node_list)
         assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
    
    async def test_valid_set_invalid_inc_txn_dep(self, setup):
        """1. Create first Transaction for set                                                                                                                                                                                                                      
        2. Create second invalid Transaction for increment with first Transaction as dependecies                                                                                                          
        3. Create Batch                                                                                                                                   
        4. Call POST /batches
        Verify the transactions. This shoud be an invalid transaction. The trird txn will be in PENDING state
        """
        LOGGER.info('Starting test for batch post')
        
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks=[]
        words = random_word_list(200)
        name=random.choice(words) 
        
        LOGGER.info("Creating intkey transactions with set operations")
        
        txns = [
            create_intkey_transaction_dep("set", [] , name, 50, signer),]
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
   
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
            
        LOGGER.info("Creating invalid intkey transactions with inc operations with dependent transactions as first transaction")
        trxn_ids = expected_trxn_ids
        txns.append(create_intkey_transaction_dep("inc", trxn_ids , name, -1, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
                
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)  
    
        LOGGER.info("Creating batches for transactions 1trn/batch")
         
        batches = [create_batch([txn], signer) for txn in txns]
         
        for batch in batches:
            data = MessageToDict(
                    batch,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
          
            batch_id = data['header_signature']
            expected_batch_ids.append(batch_id)        
           
        post_batch_list = [BatchList(batches=[batch]).SerializeToString() for batch in batches]
         
        LOGGER.info("Submitting batches to the handlers")
          
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks.append(task)
                responses = await asyncio.gather(*tasks)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
            
        LOGGER.info("Verifying the responses status")

        assert 'COMMITTED' == responses[0]['data'][0]['status']
        assert 'INVALID' == responses[1]['data'][0]['status']
                         
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
        
    async def test_valid_set_invalid_inc_DiffKey_txn_dep(self, setup):
        """1. Create first Transaction for set                                                                                                                                                                                                                      
        2. Create second invalid Transaction for increment with first Transaction as dependecies with different key                                                                                                      
        3. Create Batch                                                                                                                                   
        4. Call POST /batches
        Verify the transactions. This shoud be an invalid transaction. The trird txn will be in PENDING state
        """
        LOGGER.info('Starting test for batch post')
        
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks=[]
        words = random_word_list(200)
        name=random.choice(words) 
        
        LOGGER.info("Creating intkey transactions with set operations")
        
        txns = [
            create_intkey_transaction_dep("set", [] , name, 50, signer),]
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
   
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
            
        LOGGER.info("Creating invalid intkey transactions with inc operations with dependent transactions as first transaction")
        trxn_ids = expected_trxn_ids
        
        name = random.choice("abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz")
        txns.append(create_intkey_transaction_dep("inc", trxn_ids , name, -1, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
                
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)  
    
        LOGGER.info("Creating batches for transactions 1trn/batch")
         
        batches = [create_batch([txn], signer) for txn in txns]
         
        for batch in batches:
            data = MessageToDict(
                    batch,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
          
            batch_id = data['header_signature']
            expected_batch_ids.append(batch_id)
            
        
           
        post_batch_list = [BatchList(batches=[batch]).SerializeToString() for batch in batches]
         
        LOGGER.info("Submitting batches to the handlers")
          
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks.append(task)
                responses = await asyncio.gather(*tasks)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
            
        LOGGER.info("Verifying the responses status")

        assert 'COMMITTED' == responses[0]['data'][0]['status']
        assert 'INVALID' == responses[1]['data'][0]['status']
                         
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
        
    async def test_set_Max_txn_dep(self, setup):
        """1. Create first Transaction for set with max value                                                                                                                                                                                                                   
        2. Create second Transaction for increment with first Transaction as dependency                                                                                                      
        3. Create Batch                                                                                                                                   
        4. Call POST /batches
        Verify the transactions. The first one shoud be an invalid transaction. The second txn will be with error code 17 and Validator Timed Out
        """
        LOGGER.info('Starting test for batch post')
        
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks=[]
        words = random_word_list(200)
        name=random.choice(words) 
        
        LOGGER.info("Creating intkey transactions with set operations")
        
        txns = [
            create_intkey_transaction_dep("set", [] , name, 8888888888888888888888888, signer),]
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
   
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
            
        LOGGER.info("Creating invalid intkey transactions with inc operations with dependent transactions as first transaction")
        trxn_ids = expected_trxn_ids
        txns.append(create_intkey_transaction_dep("inc", trxn_ids , name, 2, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
                
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)  
    
        LOGGER.info("Creating batches for transactions 1trn/batch")
         
        batches = [create_batch([txn], signer) for txn in txns]
         
        for batch in batches:
            data = MessageToDict(
                    batch,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
          
            batch_id = data['header_signature']
            expected_batch_ids.append(batch_id)
            
        post_batch_list = [BatchList(batches=[batch]).SerializeToString() for batch in batches]
         
        LOGGER.info("Submitting batches to the handlers")
          
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks.append(task)
                responses = await asyncio.gather(*tasks)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
            
        LOGGER.info("Verifying the responses status")

        assert 'INVALID' == responses[0]['data'][0]['status']
        assert 'Validator Timed Out' == responses[1]['error']['title']
        assert 17 == responses[1]['error']['code']
                         
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
        
    
    async def test_invalid_set_txn_dep(self, setup):
        """1. Create first invalid Transaction for set with negative value                                                                                                                                                                                                                   
        2. Create second Transaction for increment with first invalid Transaction as dependency                                                                                                      
        3. Create Batch                                                                                                                                   
        4. Call POST /batches
        Verify the transactions. The first one shoud be an invalid transaction. The second txn will be with error code 17 and Validator Timed Out
        """
        LOGGER.info('Starting test for batch post')
        
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks=[]
        words = random_word_list(200)
        name=random.choice(words) 
        
        LOGGER.info("Creating intkey transactions with set operations")
        
        txns = [
            create_intkey_transaction_dep("set", [] , name, -1, signer),]
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
   
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
            
        LOGGER.info("Creating invalid intkey transactions with inc operations with dependent transactions as first transaction")
        trxn_ids = expected_trxn_ids
        txns.append(create_intkey_transaction_dep("inc", trxn_ids , name, 2, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
                
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)  
    
        LOGGER.info("Creating batches for transactions 1trn/batch")
         
        batches = [create_batch([txn], signer) for txn in txns]
         
        for batch in batches:
            data = MessageToDict(
                    batch,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
          
            batch_id = data['header_signature']
            expected_batch_ids.append(batch_id)
            
        post_batch_list = [BatchList(batches=[batch]).SerializeToString() for batch in batches]
         
        LOGGER.info("Submitting batches to the handlers")
          
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks.append(task)
                responses = await asyncio.gather(*tasks)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
            
        LOGGER.info("Verifying the responses status")

        assert 'INVALID' == responses[0]['data'][0]['status']
        assert 'Validator Timed Out' == responses[1]['error']['title']
        assert 17 == responses[1]['error']['code']
                         
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
        
    async def test_invalid_Address_txn_dep(self, setup):
        """1. Create first Transaction for set                                                                                                                                                                                                                   
        2. Create second dependent Transaction for increment and make the address invalid with first Transaction as dependency     
        3. Create batch ,post batch and check the response status
        4. The second transaction will be an invalid transaction
        5. Create the third transaction for decrement with first and second as dependency 
        6. Create a batch and post batch
        Verify the transaction responses. The first one will be COMMITTED and second one shoud be an invalid transaction. The third txn will be with error code 17 and Validator Timed Out
        """
        LOGGER.info('Starting test for batch post')
           
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks=[]
        words = random_word_list(200)
        name=random.choice(words) 
           
        LOGGER.info("Creating intkey transactions with set operations")
           
        txns = [
            create_intkey_transaction_dep("set", [] , name, 50, signer),]
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
      
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
               
        LOGGER.info("Creating invalid intkey transactions with inc operations with dependent transactions as first transaction")
        trxn_ids = expected_trxn_ids
        txns.append(create_invalid_Address_intkey_dep_txn("inc", trxn_ids , name, 40, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
                   
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)  
                        
        LOGGER.info("Creating batches for transactions 1trn/batch")
 
        post_batch_list = post_batch_txn(txns, expected_batch_ids, signer)
           
        LOGGER.info("Submitting batches to the handlers")
              
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks.append(task)
                responses = await asyncio.gather(*tasks)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
               
        LOGGER.info("Verifying the responses status")
             
        assert 'COMMITTED' == responses[0]['data'][0]['status']
        assert 'INVALID' == responses[1]['data'][0]['status']
          
        LOGGER.info("Creating valid intkey transactions with dec operations with dependent transactions as first and second transaction")
        trxn_ids = list(set(expected_trxn_ids))
        txns = []
        responses = []
        expected_batch_ids = []
        post_batch_list = []
        tasks = []
        txns.append(create_intkey_transaction_dep("dec", trxn_ids , name, 20, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
                   
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id) 
        
        post_batch_list = post_batch_txn(txns, expected_batch_ids, signer)
        LOGGER.info("Submitting batches to the handlers")
              
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks.append(task)
                responses = await asyncio.gather(*tasks)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
          
        LOGGER.info("Verifying the responses status")

        assert 'Validator Timed Out' == responses[0]['error']['title']
        assert 17 == responses[0]['error']['code']
                            
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
    
    async def test_Multiple_Indep_Txn_txn_dep(self, setup):
        """1.Create 5 independent Transactions for set
        2.Create second dependent transaction for set with 5 independent transactions as dependency
        3.Create third dependent Transaction for increment with second dependent Transaction as dependency     
        4.Create a batch for all the dependent transaction and post batch
        5.Check for the status
        6.Now create the batch for independent transactions and post batch
        7. Check for the response status of both independent and dependent transactions
        """
        LOGGER.info('Starting test for batch post')
         
        signer = get_signer()
        expected_trxn_ids  = []
        expected_trxn_ids_indep  = []
        expected_batch_ids = []
        expected_batch_ids_indep = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks_indep=[]
        tasks_dep=[]
        batch_ids_dep = []
        batch_ids_indep = []
        words = random_word_list(200)
        name=random.choice(words) 
         
        LOGGER.info("Creating intkey transactions with set operations")
        
        txns_Indep = [
            create_intkey_transaction("set", [] , 50, signer),
            create_intkey_transaction("set", [] , 50, signer),
            create_intkey_transaction("set", [] , 50, signer),
            create_intkey_transaction("set", [] , 50, signer),
            create_intkey_transaction("set", [] , 50, signer),]
        
        for txn in txns_Indep:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
    
            trxn_id = data['header_signature']
            expected_trxn_ids_indep.append(trxn_id)
         
        txns = [
            create_intkey_transaction_dep("set", expected_trxn_ids_indep , name, 50, signer),]
        
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
    
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
             
        LOGGER.info("Creating invalid intkey transactions with inc operations with dependent transactions as first transaction")
        trxn_ids = expected_trxn_ids
        txns.append(create_intkey_transaction_dep("inc", trxn_ids , name, 40, signer))  
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
                 
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)  

        post_batch_list = post_batch_txn(txns, expected_batch_ids, signer)
     
        LOGGER.info("Submitting batches to the handlers")
            
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks_dep.append(task)
                responses_dep = await asyncio.gather(*tasks_dep)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
             
        LOGGER.info("Verifying the responses status of dependent txns before committing the independent txns")
            
        validate_Response_Status_txn(responses_dep)

        post_batch_list = []
        tasks = []
        post_batch_list = post_batch_txn(txns_Indep, expected_batch_ids_indep, signer)
        LOGGER.info("Submitting batches to the handlers")
            
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks_indep.append(task)
                responses_indep = await asyncio.gather(*tasks_indep)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
        
        LOGGER.info("Verifying the responses of the independent txns")
            
        validate_Response_Status_txn(responses_indep)
      
        time.sleep(300)
        LOGGER.info("Waiting time to get the dependent txns to be committed")
        LOGGER.info("Verifying the responses status of dependent txns after committing the independent txns")
        validate_Response_Status_txn(responses_dep)
    
    async def test_inc_first_txn_dep(self, setup):
        """
        1.Create a dependent transactions for increment
        2.Create a dependent transaction for set for the same key with first transaction as dependent                                                                                                                                                
        3.Create batch and post the first transaction(increment) first and check the response status
        4.Post the second transaction(set)  and check the response status
        """         
        LOGGER.info('Starting test for batch post')
         
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks_inc=[]
        tasks_set = []
        words = random_word_list(200)
        name=random.choice(words) 
         
        LOGGER.info("Creating intkey transactions with inc operations")
         
        txns_inc = [
            create_intkey_transaction_dep("inc", [] , name, 10, signer),]
        for txn in txns_inc:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
    
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
              
     
        LOGGER.info("Creating batches for transactions 1trn/batch")
          
        post_batch_list = post_batch_txn(txns_inc, expected_trxn_ids, signer)
          
        LOGGER.info("Submitting batches to the handlers")
           
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks_inc.append(task)
                responses_inc = await asyncio.gather(*tasks_inc)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
             
        LOGGER.info("Verifying the responses status for first transaction")
 
        validate_Response_Status_txn(responses_inc)
        
        expected_trxn_ids  = []
        expected_batch_ids = []

        LOGGER.info("Creating invalid intkey transactions with set operations with dependent transactions as first transaction")
        trxn_ids = expected_trxn_ids
        txns_set = [
            create_intkey_transaction_dep("set", trxn_ids , name, 20, signer),]
        for txn in txns_set:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
                 
            trxn_id = data['header_signature']
             
            expected_trxn_ids.append(trxn_id) 
             
        LOGGER.info("Creating batches for transactions 1trn/batch")
        post_batch_list = post_batch_txn(txns_set, expected_trxn_ids, signer)

        LOGGER.info("Submitting batches to the handlers")
           
        try:
            async with aiohttp.ClientSession() as session: 
                for batch in post_batch_list:
                    task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                    tasks_set.append(task)
                responses_set = await asyncio.gather(*tasks_set)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
             
        LOGGER.info("Verifying the responses status for 2nd transaction")
        validate_Response_Status_txn(responses_set)             
         
        time.sleep(50)

        LOGGER.info("Verifying the responses status for first transaction again")
        validate_Response_Status_txn(responses_inc)
        
    async def test_Multiple_dep_Txn_Consecutive_dep(self, setup):
        """1.Create 5 dependent transactions for set and second one is depend on first, third is depend on second, fourth is depend on third and fifth is depend on fourth
        2. Create a batch and post the fourth and fifth transactions.
        3. Check the response status. It should not be COMMITTED.
        4. Create batch and post first, second and third transactions and check the response status. It should be COMMITTED.
        5. Now check the response for the fourth and fifth transaction. It should be COMMITTED.
        """
        LOGGER.info('Starting test for batch post')
              
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids_first = []
        expected_batch_ids_second = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks=[]
        words = random_word_list(200)
        name=random.choice(words) 
              
        LOGGER.info("Creating intkey transactions with set operations")
              
        txns = [
            create_intkey_transaction_dep("set", [] , name, 50, signer),]
             
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
         
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
                  
        LOGGER.info("Creating intkey transactions with set operations with dependent transactions as first transaction")
        value = 20
        for i in range(4):
            trxn_ids = expected_trxn_ids
            name=random.choice(words)
            
            txns.append(create_intkey_transaction_dep("set", [trxn_id] , name, value, signer))  
            for txn in [txns[-1]]:
                data = MessageToDict(
                        txn,
                        including_default_value_fields=True,
                        preserving_proto_field_name=True)
                          
                trxn_id = data['header_signature']
                expected_trxn_ids.append(trxn_id)  
            value += 10
              
        responses_last = []
        icounter = 3
        for txn in txns[3:5]:
             
            post_batch_list = post_batch_txn([txn], expected_batch_ids_first, signer)
           
            LOGGER.info("Submitting batches to the handlers")
                     
            try:
                async with aiohttp.ClientSession() as session: 
                    for batch in post_batch_list:
                        task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                        tasks.append(task)
                    responses = await asyncio.gather(*tasks)
                    validate_Response_Status_txn(responses)
                    responses_last.append(responses)
            except aiohttp.client_exceptions.ClientResponseError as error:
                LOGGER.info("Rest Api is Unreachable")
                  
            LOGGER.info("Verifying the responses status")
          
        responses_first = []
        post_batch_list = []
        expected_batch_ids = []
        icounter = 0
        for txn in txns[0:3]:
             
            post_batch_list = post_batch_txn([txn], expected_batch_ids_second, signer)
          
            LOGGER.info("Submitting batches to the handlers")
                     
            try:
                async with aiohttp.ClientSession() as session: 
                    for batch in post_batch_list:
                        task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                        tasks.append(task)
                    responses = await asyncio.gather(*tasks)
                    validate_Response_Status_txn(responses)
                    responses_first.append(responses)
            except aiohttp.client_exceptions.ClientResponseError as error:
                LOGGER.info("Rest Api is Unreachable")
                  
            LOGGER.info("Verifying the responses status")
  
        for responses in responses_first:
            validate_Response_Status_txn(responses)
        for responses in responses_last:
            validate_Response_Status_txn(responses)
                 
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
        
    async def test_Multiple_invalid_dep_Txn_Consecutive_dep(self, setup):
        """1.Create 5 dependent transactions for set and second one is depend on first, third is depend on second, 
        fourth is depend on third and fifth is depend on fourth. Fourth one will be an invalid txn
        2. Create a batch and post the fourth and fifth transactions.
        3. Check the response status. It should not be COMMITTED.
        4. Create batch and post first, second and third transactions and check the response status. It should be COMMITTED.
        5. Now check the response for the fourth and fifth transaction. It should be INVALID.
        """
        LOGGER.info('Starting test for batch post')
             
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids_first = []
        expected_batch_ids_second = []
        address = _get_client_address()
        url='{}/batches'.format(address)
        tasks=[]
        words = random_word_list(200)
        name=random.choice(words) 
             
        LOGGER.info("Creating intkey transactions with set operations")
             
        txns = [
            create_intkey_transaction_dep("set", [] , name, 50, signer),]
            
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
        
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
                 
        LOGGER.info("Creating intkey transactions with set operations with dependent transactions as first transaction")
        value = 30
        invalidValue = -20
        for i in range(4):
            trxn_ids = expected_trxn_ids
            name=random.choice(words)
            if i == 2:
                txns.append(create_intkey_transaction_dep("set", [trxn_id] , name, invalidValue, signer)) 
            else:
                txns.append(create_intkey_transaction_dep("set", [trxn_id] , name, value, signer))
                
            for txn in [txns[-1]]:
                data = MessageToDict(
                        txn,
                        including_default_value_fields=True,
                        preserving_proto_field_name=True)
                         
                trxn_id = data['header_signature']
                expected_trxn_ids.append(trxn_id)

        responses_last = []
        icounter = 3
        for txn in txns[3:5]:
            
            post_batch_list = post_batch_txn([txn], expected_batch_ids_first, signer)
          
            LOGGER.info("Submitting batches to the handlers")
                    
            try:
                async with aiohttp.ClientSession() as session: 
                    for batch in post_batch_list:
                        task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                        tasks.append(task)
                    responses = await asyncio.gather(*tasks)
                    responses_last.append(responses)
            except aiohttp.client_exceptions.ClientResponseError as error:
                LOGGER.info("Rest Api is Unreachable")
                 
            LOGGER.info("Verifying the responses status")
 
        responses_first = []
        post_batch_list = []
        icounter = 0
        for txn in txns[0:3]:           
            post_batch_list = post_batch_txn([txn], expected_batch_ids_second, signer)
           
            LOGGER.info("Submitting batches to the handlers")
                    
            try:
                async with aiohttp.ClientSession() as session: 
                    for batch in post_batch_list:
                        task = asyncio.ensure_future(async_post_batch(url,session,data=batch))
                        tasks.append(task)
                    responses = await asyncio.gather(*tasks)
                    validate_Response_Status_txn(responses)
                    responses_first.append(responses)
            except aiohttp.client_exceptions.ClientResponseError as error:
                LOGGER.info("Rest Api is Unreachable")
                 
        LOGGER.info("Verifying the responses status")
 
        for responses in responses_first:
            validate_Response_Status_txn(responses)
        for responses in responses_last:
            validate_Response_Status_txn(responses)
                       
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True
