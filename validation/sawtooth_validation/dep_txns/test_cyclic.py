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

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

from google.protobuf.json_format import MessageToDict


from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory
from sawtooth_signing import ParseError
from sawtooth_signing.secp256k1 import Secp256k1PrivateKey

from sawtooth_rest_api.protobuf.batch_pb2 import Batch
from sawtooth_rest_api.protobuf.batch_pb2 import BatchList
from sawtooth_rest_api.protobuf.batch_pb2 import BatchHeader
from sawtooth_rest_api.protobuf.transaction_pb2 import TransactionHeader
from sawtooth_rest_api.protobuf.transaction_pb2 import Transaction
from sawtooth_rest_api.protobuf.smallbank_pb2 import *

from utils import post_batch, get_state_list , get_blocks , get_transactions, \
                  get_batches , get_state_address, check_for_consensus,\
                  _get_node_list, _get_node_chains
                  

from payload import get_signer, create_intkey_transaction, create_batch,\
                    create_intkey_same_transaction


class TestCyclicDependentTxns():
    def test_valid_dependent_txns(self):
        signer = get_signer()
        expected_trxn_ids  = []
        expected_batch_ids = []
        txns = [
            create_intkey_transaction("set", [] , 50 , signer),
        ]        
        
        for txn in txns:
            data = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
    
            trxn_id = data['header_signature']
            expected_trxn_ids.append(trxn_id)
        
    
        LOGGER.info("Creating batches for transactions 1trn/batch")
        txns.append(create_intkey_transaction("set", expected_trxn_ids , 50 , signer))
        
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
    
        for batch in post_batch_list:
            try:
                response = post_batch(batch)
            except urllib.error.HTTPError as error:
                data = error.fp.read().decode('utf-8')
                LOGGER.info(data)
        
        account = Account(customer_id=1, customer_name="a", savings_balance=0, checking_balance=0)
        print(account)