# Copyright 2018 Intel Corporation
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

import logging
import time
import hashlib

from sawtooth_sdk.protobuf.smallbank_pb2 import *

from sawtooth_processor_test.message_factory import MessageFactory

FAMILY_NAME='smallbank'

SMALLBANK_ADDRESS_PREFIX = hashlib.sha512(
    'smallbank'.encode('utf-8')).hexdigest()[0:6]


class SmallBankMessageFactory:
    def __init__(self, signer=None):
        self._factory = MessageFactory(
            family_name=FAMILY_NAME,
            family_version='1.0',
            namespace=SMALLBANK_ADDRESS_PREFIX,
            signer=signer)
        
        self.public_key = self._factory.get_public_key()
        self.payload=SmallbankTransactionPayload()
    
    
    def create_payload(self, address, payload, deps):
        return self._create_transaction(
            payload=payload.SerializeToString(),
            inputs=address,
            outputs=address,
            deps=deps
        )
        

    def create_account(self, cust_id, name, amount):
        self.payload.payload_type=1
        self.payload.create_account.customer_id=cust_id
        self.payload.create_account.customer_name=name
        self.payload.create_account.initial_savings_balance=amount
        self.payload.create_account.initial_checking_balance=amount
        return self.payload
    
    def deposit_checking(self, cust_id, amount):
        self.payload.payload_type=2
        self.payload.deposit_checking.customer_id=cust_id
        self.payload.deposit_checking.amount=amount
        return self.payload
    
    def write_check(self, cust_id, amount):
        self.payload.payload_type=3
        self.payload.write_check.customer_id=cust_id
        self.payload.write_check.amount=amount
        return self.payload
    
    def transact_saving(self,cust_id, amount):
        self.payload.payload_type=4
        self.payload.transact_savings.customer_id=cust_id
        self.payload.transact_savings.amount=amount
        return self.payload
    
    def send_payment(self, source_cust_id, dest_cust_id, amount):
        self.payload.payload_type=5
        self.payload.send_payment.source_customer_id=source_cust_id
        self.payload.send_payment.dest_customer_id=dest_cust_id
        self.payload.send_payment.amount=amount
        return self.payload
    
    def amalgate_accounts(self):
        self.payload.payload_type=6
        self.payload.amalgamate.source_customer_id=source_cust_id
        self.payload.amalgamate.dest_customer_id=dest_cust_id
        return self.payload
    
    def _create_transaction(self, payload, inputs, outputs, deps):
        return self._factory.create_transaction(
            payload, inputs, outputs, deps)

    def _create_batch(self, txns):
        return self._factory.create_batch(txns)