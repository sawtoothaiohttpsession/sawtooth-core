# Copyright 2017 Intel Corporation
# Copyright 2018 Cargill Incorporated
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

import logging
import hashlib
import time

from sawtooth_processor_test.message_factory import MessageFactory

from sawtooth_sdk.protobuf.payload_pb2 import *
from sawtooth_sdk.protobuf.property_pb2 import *


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

SUPPLYCHAIN_ADDRESS_PREFIX = hashlib.sha512(
    'supplychain'.encode('utf-8')).hexdigest()[0:6]
    
class SupplyChainMessageFactory:
    def __init__(self, signer=None):
        self._factory = MessageFactory(
            family_name='supplychain',
            family_version='1.1',
            namespace=SUPPLYCHAIN_ADDRESS_PREFIX,
            signer=signer)

        self.payload= SCPayload()
        
    def create_payload(self, address, payload, deps):
        return self._create_transaction(
            payload=payload.SerializeToString(),
            inputs=address,
            outputs=address,
            deps=deps
        )

    def create_agent(self, name):
        self.payload.action=0
        self.payload.timestamp=round(time.time())
        self.payload.create_agent.name=name
        return self.payload
   
    def _create_transaction(self, payload, inputs, outputs, deps):
        return self._factory.create_transaction(
            payload, inputs, outputs, deps)

    def _create_batch(self, txns):
        return self._factory.create_batch(txns)