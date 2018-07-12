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
  
from fixtures import break_genesis,invalid_batch
from utils import get_batches, post_batch , get_transactions, get_transaction , get_blocks, \
                  get_state_list

from base import RestApiBaseTest


pytestmark = [pytest.mark.get]

  
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
  

class TestList(RestApiBaseTest):
    """This class tests the batch list with different parameters
    """
    def test_api_get_batch_list(self, setup):
        """Tests the batch list by submitting intkey batches
        """
        signer_key = setup['signer_key']
        expected_head = setup['expected_head']
        expected_batches = setup['expected_batches']
        expected_txns = setup['expected_txns']
              
        try:   
            response = get_batches()
        except urllib.error.HTTPError as error:
            LOGGER.info("Rest Api is Unreachable")
           
        batches = response['data'][:-1]  
                     
        self.assert_check_batch_seq(batches, expected_batches, expected_txns)
        self.assert_valid_head(response, expected_head)
               
            
    def test_api_get_batch_list_head(self, setup):   
        """Tests that GET /batches is reachable with head parameter 
        """
        LOGGER.info("Starting test for batch with head parameter")
        expected_head = setup['expected_head']
                 
        try:
            response = get_batches(head_id=expected_head)
        except  urllib.error.HTTPError as error:
            LOGGER.info("Rest Api not reachable")
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
                 
        assert response['head'] == expected_head , "request is not correct"
          
    def test_api_get_batch_list_bad_head(self, setup):   
        """Tests that GET /batches is unreachable with bad head parameter 
        """       
        LOGGER.info("Starting test for batch with bad head parameter")
        bad_head = 'f' 
                      
        try:
            batch_list = get_batches(head_id=bad_head)
        except urllib.error.HTTPError as error:
            LOGGER.info("Rest Api is not reachable")
            data = json.loads(error.fp.read().decode('utf-8'))
            if data:
                LOGGER.info(data['error']['title'])
                LOGGER.info(data['error']['message'])
                assert data['error']['code'] == 60
                assert data['error']['title'] == 'Invalid Resource Id'
               
    def test_api_get_batch_list_id(self, setup):   
        """Tests that GET /batches is reachable with id as parameter 
        """
        LOGGER.info("Starting test for batch with id parameter")
                      
        batch_ids   =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
                     
        try:
            response = get_batches(id=expected_id)
        except:
            LOGGER.info("Rest Api is not reachable")
                    
                    
        assert response['head'] == expected_head, "request is not correct"
        assert response['paging']['start'] == None , "request is not correct"
        assert response['paging']['limit'] == None , "request is not correct"
                
    def test_api_get_batch_list_bad_id(self, setup):   
        """Tests that GET /batches is unreachable with bad id parameter 
        """
        LOGGER.info("Starting test for batch with bad id parameter")
        bad_id = 'f' 
                      
        try:
            batch_list = get_batches(head_id=bad_id)
        except urllib.error.HTTPError as error:
            LOGGER.info("Rest Api is not reachable")
            data = json.loads(error.fp.read().decode('utf-8'))
            if data:
                LOGGER.info(data['error']['title'])
                LOGGER.info(data['error']['message'])
                assert data['error']['code'] == 60
                assert data['error']['title'] == 'Invalid Resource Id'
              
    def test_api_get_batch_list_head_and_id(self, setup):   
        """Tests GET /batches is reachable with head and id as parameters 
        """
        LOGGER.info("Starting test for batch with head and id parameter")
        batch_ids =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
                       
                
        response = get_batches(head_id=expected_head , id=expected_id)
                      
        assert response['head'] == expected_head , "head is not matching"
        assert response['paging']['start'] == None ,  "start parameter is not correct"
        assert response['paging']['limit'] == None ,  "request is not correct"
        assert bool(response['data']) == True
                
               
    def test_api_get_paginated_batch_list(self, setup):   
        """Tests GET /batches is reachbale using paging parameters 
        """
        LOGGER.info("Starting test for batch with paging parameters")
        batch_ids   =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        start = 1
        limit = 1
                   
        try:
            response = get_batches(start=start , limit=limit)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 54
            
    def test_api_get_batch_list_invalid_start(self, setup):   
        """Tests that GET /batches is unreachable with invalid start parameter 
        """
        LOGGER.info("Starting test for batch with invalid start parameter")
        batch_ids   =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        start = -1
                        
        try:  
            response = get_batches(start=start)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 54
         
    def test_api_get_batch_list_invalid_limit(self, setup):   
        """Tests that GET /batches is unreachable with bad limit parameter 
        """
        LOGGER.info("Starting test for batch with bad limit parameter")
        batch_ids = setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        limit = 0
                    
        try:  
            response = get_batches(limit=limit)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 53
   
    def test_api_get_batch_list_no_count(self, setup):   
        """Tests that GET /batches is unreachable with bad limit parameter 
        """
        LOGGER.info("Starting test for batch with bad limit parameter")
        batch_ids =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        count = 0
                    
        try:  
            response = get_batches(count=count)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 53
                  
    def test_api_get_batch_list_reversed(self, setup):   
        """verifies that GET /batches is unreachable with bad head parameter 
        """
        LOGGER.info("Starting test for batch with bad head parameter")
        batch_ids = setup['batch_ids']
        expected_head = setup['expected_head']
        reverse = True
                        
        try:
            response = get_batches(reverse=reverse)
        except urllib.error.HTTPError as error:
            assert response.code == 400
                       
        assert response['head'] == expected_head , "request is not correct"
        assert response['paging']['start'] == None ,  "request is not correct"
        assert response['paging']['limit'] == None ,  "request is not correct"
        assert bool(response['data']) == True
 
    def test_api_get_transaction_list(self, setup):
        """Tests the transaction list after submitting intkey batches
        """
        signer_key = setup['signer_key']
        expected_head = setup['expected_head']
        expected_txns = setup['expected_txns']
         
        try:   
            response = get_transactions()
        except urllib.error.HTTPError as error:
            LOGGER.info("Rest Api is Unreachable")
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
              
        txns = response['data'][:-1]
                        
#         self.assert_valid_head(response , expected_head)
#         self.assert_valid_link()
#         self.assert_valid_data_list()
        self.assert_check_transaction_seq(txns, expected_txns)
     
    def test_api_get_transaction_list_head(self, setup):   
        """Tests that GET /transactions is reachable with head parameter 
        """
        LOGGER.info("Starting test for transactions with head parameter")
        expected_head = setup['expected_head']
                 
        try:
            response = get_transactions(head_id=expected_head)
        except  urllib.error.HTTPError as error:
            LOGGER.info("Rest Api not reachable")
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
                 
        assert response['head'] == expected_head , "request is not correct"
          
    def test_api_get_transaction_list_bad_head(self, setup):   
        """Tests that GET /transactions is unreachable with bad head parameter 
        """       
        LOGGER.info("Starting test for transactions with bad head parameter")
        bad_head = 'f' 
                      
        try:
            batch_list = get_transactions(head_id=bad_head)
        except urllib.error.HTTPError as error:
            LOGGER.info("Rest Api is not reachable")
            data = json.loads(error.fp.read().decode('utf-8'))
            if data:
                LOGGER.info(data['error']['title'])
                LOGGER.info(data['error']['message'])
                assert data['error']['code'] == 60
                assert data['error']['title'] == 'Invalid Resource Id'
               
    def test_api_get_transaction_list_id(self, setup):   
        """Tests that GET /transactions is reachable with id as parameter 
        """
        LOGGER.info("Starting test for transactions with id parameter")
                      
        batch_ids   =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
                     
        try:
            response = get_transactions(id=expected_id)
        except:
            LOGGER.info("Rest Api is not reachable")
                    
                    
        assert response['head'] == expected_head, "request is not correct"
        assert response['paging']['start'] == None , "request is not correct"
        assert response['paging']['limit'] == None , "request is not correct"
                
    def test_api_get_transaction_list_bad_id(self, setup):   
        """Tests that GET /transactions is unreachable with bad id parameter 
        """
        LOGGER.info("Starting test for transactions with bad id parameter")
        bad_id = 'f' 
                      
        try:
            batch_list = get_transactions(head_id=bad_id)
        except urllib.error.HTTPError as error:
            LOGGER.info("Rest Api is not reachable")
            data = json.loads(error.fp.read().decode('utf-8'))
            if data:
                LOGGER.info(data['error']['title'])
                LOGGER.info(data['error']['message'])
                assert data['error']['code'] == 60
                assert data['error']['title'] == 'Invalid Resource Id'
              
    def test_api_get_transaction_list_head_and_id(self, setup):   
        """Tests GET /transactions is reachable with head and id as parameters 
        """
        LOGGER.info("Starting test for transactions with head and id parameter")
        batch_ids =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
                       
                
        response = get_transactions(head_id=expected_head , id=expected_id)
                      
        assert response['head'] == expected_head , "head is not matching"
        assert response['paging']['start'] == None ,  "start parameter is not correct"
        assert response['paging']['limit'] == None ,  "request is not correct"               
               
    def test_api_get_paginated_transaction_list(self, setup):   
        """Tests GET /transactions is reachbale using paging parameters 
        """
        LOGGER.info("Starting test for transactions with paging parameters")
        batch_ids   =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        start = 1
        limit = 1
                   
        try:
            response = get_transactions(start=start , limit=limit)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 54
     
    def test_api_get_transaction_bad_paging(self, setup):   
        """Tests GET /transactions is reachbale using bad paging parameters 
        """
        LOGGER.info("Starting test for transactions with bad paging parameters")
        batch_ids   =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        start = -1
        limit = -1
                   
        try:
            response = get_transactions(start=start , limit=limit)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 53
                
    def test_api_get_transaction_list_invalid_start(self, setup):   
        """Tests that GET /transactions is unreachable with invalid start parameter 
        """
        LOGGER.info("Starting test for transactions with invalid start parameter")
        batch_ids   =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        start = -1
                        
        try:  
            response = get_transactions(start=start)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 54
         
    def test_api_get_transaction_list_invalid_limit(self, setup):   
        """Tests that GET /transactions is unreachable with bad limit parameter 
        """
        LOGGER.info("Starting test for transactions with bad limit parameter")
        batch_ids = setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        limit = 0
                    
        try:  
            response = get_transactions(limit=limit)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 53
     
    def test_api_get_transaction_list_count(self, setup):   
        """Tests that GET /transactions with count parameter 
        """
        LOGGER.info("Starting test for transactions with count parameter")
        batch_ids =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        count = 1
                    
        try:  
            response = get_transactions(count=count)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
         
        assert response['head'] == expected_head , "head is not matching"
        assert response['paging']['start'] == None ,  "start parameter is not correct"
        assert response['paging']['limit'] == None ,  "request is not correct"
   
    def test_api_get_transaction_list_no_count(self, setup):   
        """Tests that GET /transactions with no count parameter 
        """
        LOGGER.info("Starting test for transactions with no count parameter")
        batch_ids =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        count = 0
                    
        try:  
            response = get_transactions(count=count)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 53
                    
    def test_api_get_transaction_list_reversed(self, setup):   
        """verifies that GET /transactions with list reversed
        """
        LOGGER.info("Starting test for transactions with list reversed")
        batch_ids = setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        reverse = True
                        
        try:
            response = get_transactions(reverse=reverse)
        except urllib.error.HTTPError as error:
            assert response.code == 400
                       
        assert response['head'] == expected_head , "request is not correct"
        assert response['paging']['start'] == None ,  "request is not correct"
        assert response['paging']['limit'] == None ,  "request is not correct"
        assert bool(response['data']) == True

    def test_api_get_block_list(self, setup):
        """Tests the batch list by submitting intkey batches
        """
        signer_key = setup['signer_key']
        expected_head = setup['expected_head']
        expected_batches = setup['expected_batches']
        expected_txns = setup['expected_txns']
              
        try:   
            response = get_blocks()
        except urllib.error.HTTPError as error:
            LOGGER.info("Rest Api is Unreachable")
           
        batches = response['data'][:-1]  
                     
        assert response['head'] == expected_head , "request is not correct"
        assert response['paging']['start'] == None ,  "request is not correct"
        assert response['paging']['limit'] == None ,  "request is not correct"
        assert bool(response['data']) == True
                
    def test_api_get_block_list_head(self, setup):   
        """Tests that GET /batches is reachable with head parameter 
        """
        LOGGER.info("Starting test for batch with head parameter")
        expected_head = setup['expected_head']
                 
        try:
            response = get_blocks(head_id=expected_head)
        except  urllib.error.HTTPError as error:
            LOGGER.info("Rest Api not reachable")
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
                 
        assert response['head'] == expected_head , "request is not correct"
          
    def test_api_get_block_list_bad_head(self, setup):   
        """Tests that GET /batches is unreachable with bad head parameter 
        """       
        LOGGER.info("Starting test for batch with bad head parameter")
        bad_head = 'f' 
                      
        try:
            batch_list = get_blocks(head_id=bad_head)
        except urllib.error.HTTPError as error:
            LOGGER.info("Rest Api is not reachable")
            data = json.loads(error.fp.read().decode('utf-8'))
            if data:
                LOGGER.info(data['error']['title'])
                LOGGER.info(data['error']['message'])
                assert data['error']['code'] == 60
                assert data['error']['title'] == 'Invalid Resource Id'
               
    def test_api_get_block_list_id(self, setup):   
        """Tests that GET /batches is reachable with id as parameter 
        """
        LOGGER.info("Starting test for batch with id parameter")
                      
        block_ids   =  setup['block_ids']
        expected_head = setup['expected_head']
        expected_id = block_ids[0]
                     
        try:
            response = get_blocks(id=expected_id)
        except:
            LOGGER.info("Rest Api is not reachable")
                    
                    
        assert response['head'] == expected_head, "request is not correct"
        assert response['paging']['start'] == None , "request is not correct"
        assert response['paging']['limit'] == None , "request is not correct"
                
    def test_api_get_block_list_bad_id(self, setup):   
        """Tests that GET /batches is unreachable with bad id parameter 
        """
        LOGGER.info("Starting test for batch with bad id parameter")
        bad_id = 'f' 
                      
        try:
            batch_list = get_blocks(head_id=bad_id)
        except urllib.error.HTTPError as error:
            LOGGER.info("Rest Api is not reachable")
            data = json.loads(error.fp.read().decode('utf-8'))
            if data:
                LOGGER.info(data['error']['title'])
                LOGGER.info(data['error']['message'])
                assert data['error']['code'] == 60
                assert data['error']['title'] == 'Invalid Resource Id'
              
    def test_api_get_block_list_head_and_id(self, setup):   
        """Tests GET /batches is reachable with head and id as parameters 
        """
        LOGGER.info("Starting test for batch with head and id parameter")
        block_ids =  setup['block_ids']
        expected_head = setup['expected_head']
        expected_id = block_ids[0]
                       
                
        response = get_blocks(head_id=expected_head , id=expected_id)
                      
        assert response['head'] == expected_head , "head is not matching"
        assert response['paging']['start'] == None ,  "start parameter is not correct"
        assert response['paging']['limit'] == None ,  "request is not correct"
        assert bool(response['data']) == True
                
               
    def test_api_get_paginated_block_list(self, setup):   
        """Tests GET /batches is reachbale using paging parameters 
        """
        LOGGER.info("Starting test for batch with paging parameters")
        block_ids   =  setup['block_ids']
        expected_head = setup['expected_head']
        expected_id = block_ids[0]
        start = 1
        limit = 1
                   
        try:
            response = get_blocks(start=start , limit=limit)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 54
                
    def test_api_get_block_list_invalid_start(self, setup):   
        """Tests that GET /batches is unreachable with invalid start parameter 
        """
        LOGGER.info("Starting test for batch with invalid start parameter")
        block_ids   =  setup['block_ids']
        expected_head = setup['expected_head']
        expected_id = block_ids[0]
        start = -1
                        
        try:  
            response = get_blocks(start=start)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 54
         
    def test_api_get_block_list_invalid_limit(self, setup):   
        """Tests that GET /batches is unreachable with bad limit parameter 
        """
        LOGGER.info("Starting test for batch with bad limit parameter")
        block_ids = setup['block_ids']
        expected_head = setup['expected_head']
        expected_id = block_ids[0]
        limit = 0
                    
        try:  
            response = get_blocks(limit=limit)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 53
   
    def test_api_get_block_list_no_count(self, setup):   
        """Tests that GET /batches is unreachable with bad limit parameter 
        """
        LOGGER.info("Starting test for batch with bad limit parameter")
        block_ids =  setup['block_ids']
        expected_head = setup['expected_head']
        expected_id = block_ids[0]
        limit = 0
                    
        try:  
            response = get_blocks(limit=limit)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 53
                    
    def test_api_get_block_list_reversed(self, setup):   
        """verifies that GET /batches is unreachable with bad head parameter 
        """
        LOGGER.info("Starting test for batch with bad head parameter")
        block_ids = setup['block_ids']
        expected_head = setup['expected_head']
        expected_id = block_ids[0]
        reverse = True
                        
        try:
            response = get_blocks(reverse=reverse)
        except urllib.error.HTTPError as error:
            assert response.code == 400
                       
        assert response['head'] == expected_head , "request is not correct"
        assert response['paging']['start'] == None ,  "request is not correct"
        assert response['paging']['limit'] == None ,  "request is not correct"
        assert bool(response['data']) == True
    
    def test_api_get_state_list(self, setup):
        """Tests the state list by submitting intkey batches
        """
        signer_key = setup['signer_key']
        expected_head = setup['expected_head']
        expected_batches = setup['expected_batches']
        expected_txns = setup['expected_txns']
              
        try:   
            response = get_state_list()
        except urllib.error.HTTPError as error:
            LOGGER.info("Rest Api is Unreachable")
           
        batches = response['data'][:-1]  
                     
        assert response['head'] == expected_head , "request is not correct"
        assert response['paging']['start'] == None ,  "request is not correct"
        assert response['paging']['limit'] == None ,  "request is not correct"
        assert bool(response['data']) == True
                                  
    def test_api_get_state_list_head(self, setup):   
        """Tests that GET /state is reachable with head parameter 
        """
        LOGGER.info("Starting test for state with head parameter")
        expected_head = setup['expected_head']
                 
        try:
            response = get_state_list(head_id=expected_head)
        except  urllib.error.HTTPError as error:
            LOGGER.info("Rest Api not reachable")
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
                 
        assert response['head'] == expected_head , "request is not correct"
          
    def test_api_get_state_list_bad_head(self, setup):   
        """Tests that GET /state is unreachable with bad head parameter 
        """       
        LOGGER.info("Starting test for state with bad head parameter")
        bad_head = 'f' 
                      
        try:
            batch_list = get_state_list(head_id=bad_head)
        except urllib.error.HTTPError as error:
            LOGGER.info("Rest Api is not reachable")
            data = json.loads(error.fp.read().decode('utf-8'))
            if data:
                LOGGER.info(data['error']['title'])
                LOGGER.info(data['error']['message'])
                assert data['error']['code'] == 60
                assert data['error']['title'] == 'Invalid Resource Id'
     
    def test_api_get_state_list_address(self, setup):   
        """Tests that GET /state is reachable with address parameter 
        """
        LOGGER.info("Starting test for state with address parameter")
        expected_head = setup['expected_head']
        address = setup['address'][0]
                 
        try:
            response = get_state_list(address=address)
        except  urllib.error.HTTPError as error:
            LOGGER.info("Rest Api not reachable")
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
                 
        assert response['head'] == expected_head , "request is not correct"
          
    def test_api_get_state_list_bad_address(self, setup):   
        """Tests that GET /state is unreachable with bad address parameter 
        """       
        LOGGER.info("Starting test for state with bad address parameter")
        bad_address = 'f' 
                      
        try:
            batch_list = get_state_list(address=bad_address)
        except urllib.error.HTTPError as error:
            LOGGER.info("Rest Api is not reachable")
            data = json.loads(error.fp.read().decode('utf-8'))
            if data:
                LOGGER.info(data['error']['title'])
                LOGGER.info(data['error']['message'])
                assert data['error']['code'] == 60
                assert data['error']['title'] == 'Invalid Resource Id'
                                          
    def test_api_get_paginated_state_list(self, setup):   
        """Tests GET /state is reachbale using paging parameters 
        """
        LOGGER.info("Starting test for state with paging parameters")
        batch_ids   =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        start = 1
        limit = 1
                   
        try:
            response = get_state_list(start=start , limit=limit)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 54
     
    def test_api_get_state_list_bad_paging(self, setup):   
        """Tests GET /state is reachbale using bad paging parameters 
        """
        LOGGER.info("Starting test for state with bad paging parameters")
        batch_ids   =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        start = -1
        limit = -1
                   
        try:
            response = get_state_list(start=start , limit=limit)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 53
                
    def test_api_get_state_list_invalid_start(self, setup):   
        """Tests that GET /state is unreachable with invalid start parameter 
        """
        LOGGER.info("Starting test for state with invalid start parameter")
        batch_ids   =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        start = -1
                        
        try:  
            response = get_state_list(start=start)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 54
         
    def test_api_get_state_list_invalid_limit(self, setup):   
        """Tests that GET /state is unreachable with bad limit parameter 
        """
        LOGGER.info("Starting test for state with bad limit parameter")
        batch_ids = setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        limit = 0
                    
        try:  
            response = get_state_list(limit=limit)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 53
     
    def test_api_get_state_list_count(self, setup):   
        """Tests that GET /state is unreachable with bad limit parameter 
        """
        LOGGER.info("Starting test for state with bad limit parameter")
        expected_head = setup['expected_head']
        count = 1
                    
        try:  
            response = get_state_list(count=count)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
         
        assert response['head'] == expected_head , "request is not correct"
   
    def test_api_get_state_list_no_count(self, setup):   
        """Tests that GET /state is unreachable with bad limit parameter 
        """
        LOGGER.info("Starting test for state with bad limit parameter")
        batch_ids =  setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        count = 0
                    
        try:  
            response = get_state_list(count=count)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 53
                    
    def test_api_get_state_list_reversed(self, setup):   
        """verifies that GET /state is unreachable with bad head parameter 
        """
        LOGGER.info("Starting test for state with bad head parameter")
        batch_ids = setup['batch_ids']
        expected_head = setup['expected_head']
        expected_id = batch_ids[0]
        reverse = True
                        
        try:
            response = get_state_list(reverse=reverse)
        except urllib.error.HTTPError as error:
            assert response.code == 400
                       
        assert response['head'] == expected_head , "request is not correct"
        assert response['paging']['start'] == None ,  "request is not correct"
        assert response['paging']['limit'] == None ,  "request is not correct"
        assert bool(response['data']) == True
    
    def test_rest_api_post_bad_protobuf(self):
        """Tests when a bad protobuf is passed 
        """
        bad_protobuf=b'a'
        
        try:
            response = post_batch(batch=bad_protobuf)
        except urllib.error.HTTPError as error:
            data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(data['error']['title'])
            LOGGER.info(data['error']['message'])
            assert data['error']['code'] == 35
