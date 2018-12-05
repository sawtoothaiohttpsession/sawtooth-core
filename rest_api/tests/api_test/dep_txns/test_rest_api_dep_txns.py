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

from google.protobuf.json_format import MessageToDict

from sawtooth_rest_api.protobuf.batch_pb2 import BatchList

from utils import post_batch, get_state_list , get_blocks , get_transactions, \
                  get_batches , get_state_address, check_for_consensus,\
                  _get_node_list, _get_node_chains, post_batch_no_endpoint,\
                  get_reciepts, _get_client_address, state_count, get_batch_id, get_transaction_id
     
from utils import _get_client_address

from payload import get_signer, create_intkey_transaction, create_batch,\
                    create_intkey_same_transaction,  \
                    create_intkey_transaction_dep, random_word_list 

from base import RestApiBaseTest

from fixtures import setup_empty_trxs_batch, setup_invalid_txns,setup_invalid_txns_min,\
                     setup_invalid_txns_max, setup_valinv_txns, setup_invval_txns, \
                     setup_same_txns, setup_valid_txns, setup_invalid_txns_fn,\
                     setup_invalid_invaddr
                  
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
                time.sleep(60)
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
                time.sleep(60)
                responses = await asyncio.gather(*tasks)
        except aiohttp.client_exceptions.ClientResponseError as error:
            LOGGER.info("Rest Api is Unreachable")
            
        LOGGER.info("Verifying the responses status")

        assert 'COMMITTED' == responses[0]['data'][0]['status']
        assert 'INVALID' == responses[1]['data'][0]['status']
                         
        node_list = _get_node_list()
        chains = _get_node_chains(node_list)
        assert check_for_consensus(chains , BLOCK_TO_CHECK_CONSENSUS) == True

    
