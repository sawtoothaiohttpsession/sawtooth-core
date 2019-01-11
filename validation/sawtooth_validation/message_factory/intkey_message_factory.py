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

import logging
import time
import hashlib

from sawtooth_processor_test.message_factory import MessageFactory

INTKEY_ADDRESS_PREFIX = hashlib.sha512(
    'intkey'.encode('utf-8')).hexdigest()[0:6]


class IntkeyMessageFactory:
    def __init__(self, signer=None):
        self._factory = MessageFactory(
            family_name='intkey',
            family_version='1.0',
            namespace=INTKEY_ADDRESS_PREFIX,
            signer=signer)

    def _dumps(self, obj):
        return cbor.dumps(obj, sort_keys=True)

    def _loads(self, data):
        return cbor.loads(data)

    def _create_txn(self, txn_function, verb, name, value):
        payload = self._dumps({'Verb': verb, 'Name': name, 'Value': value})

        addresses = [make_intkey_address(name)]

        return txn_function(payload, addresses, addresses, [])

    def create_transaction(self, verb, name, value,):
        txn_function = self._factory.create_transaction
        return self._create_txn(txn_function, verb, name, value)

    def create_batch(self, triples):
        txns = [
            self.create_transaction(verb, name, value)
            for verb, name, value in triples
        ]

        return self._factory.create_batch(txns)