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
import hashlib

from google.protobuf.json_format import MessageToDict


from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory

from sawtooth_validation.message_factory.supplychain_message_factory\
                        import SupplyChainMessageFactory

from sawtooth_validation.message_factory.smallbank_message_factory\
                        import SmallBankMessageFactory

from sawtooth_validation.message_factory.intkey_message_factory\
                        import IntkeyMessageFactory

from sawtooth_validation.val_factory import Transaction
                        
                             
class DependentTxns(Transaction):
    def __init__(self):
        signer = self.get_signer()
        self.factory=SmallBankMessageFactory(signer=signer)

    def get_signer(self):
        context = create_context('secp256k1')
        private_key = context.new_random_private_key()
        signer = CryptoFactory(context).new_signer(private_key)
        return signer
    
    def create_batch(self,txns):
        return self.factory._create_batch(txns)
    
    def _create_txn(self,txn):
        self.factory.create_payload(address,payload)
        return
        
    def _calculate_address(self,cust1):
        NAMESPACE= hashlib.sha512('smallbank'.encode('utf-8')).hexdigest()[0:6] 
        CUST_HEX= hashlib.sha512(str(cust1).encode('utf-8')).hexdigest()[0:64]
        addr1=NAMESPACE+CUST_HEX
        return addr1
    
    def _create_account(self,cust_id,name,amount,deps=None):
        acc = self.factory.create_account(cust_id,name,amount)
        address=[self._calculate_address(cust_id)]
        print(deps)
        txn = self.factory.create_payload(address,acc,deps)
        return txn
    
    
    def _create_send_payment(self,source_cust_id, dest_cust_id,amount,deps=None):
        acc = self.factory.send_payment(source_cust_id,dest_cust_id,amount)
        print(acc)
        address1=self._calculate_address(source_cust_id)
        address2=self._calculate_address(dest_cust_id)
        address_list=[address1,address2]
        print(address_list)
        txn = self.factory.create_payload(address_list,acc,deps)
        return txn
        
    
    def _create_deposit_checking(self,cust_id,amount,deps=None):
        acc = self.factory.deposit_checking(cust_id,amount)
        print(acc)
        address=[self._calculate_address(cust_id)]
        txn = self.factory.create_payload(address,acc,deps)
        return txn


class CyclicTxns(Transaction):
    def __init__(self,signer):
        context = create_context('secp256k1')
        private_key = context.new_random_private_key()
        signer = CryptoFactory(context).new_signer(private_key)
        self.payload=SmallBankMessageFactory(signer=signer)
    
    def get_signer(self):
        context = create_context('secp256k1')
        private_key = context.new_random_private_key()
        signer = CryptoFactory(context).new_signer(private_key)
        return signer

    

class ApiTxns(Transaction):
    def __init__(self,signer):
        self.factory=IntkeyMessageFactory(signer=signer)
        context = create_context('secp256k1')
        private_key = context.new_random_private_key()
        signer = CryptoFactory(context).new_signer(private_key)
        
    def _create_empty_txn(self):
        signer = get_signer()
        header = BatchHeader(
            signer_public_key=signer.get_public_key().as_hex(),
            transaction_ids=[])
    
        header_bytes = header.SerializeToString()
    
        signature = signer.sign(header_bytes)
    
        batch = Batch(
            header=header_bytes,
            transactions=[],
            header_signature=signature)
        
        return batch
    
    def _create_invalid_txn(self):
        payload=self.payload
        signer = get_signer()
        data = {}
        expected_trxns  = {}
        expected_batches = []
        address = _get_client_address()
        
        LOGGER.info("Creating intkey transactions with set operations")
        
        txns = [
            create_invalid_intkey_transaction("set", [] , 50 , signer),
        ]
        
        for txn in txns:
            dict = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
                    
            expected_trxns['trxn_id'] = [dict['header_signature']]
    
        
        LOGGER.info("Creating batches for transactions 1trn/batch")
    
        batches = [create_batch([txn], signer) for txn in txns]
        
        for batch in batches:
            dict = MessageToDict(
                    batch,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
    
            batch_id = dict['header_signature']
            expected_batches.append(batch_id)
        
        data['expected_txns'] = expected_trxns['trxn_id'][::-1]
        data['expected_batches'] = expected_batches[::-1]
        data['address'] = address
    
        post_batch_list = [BatchList(batches=[batch]).SerializeToString() for batch in batches]
        
        for batch in post_batch_list:
            try:
                response = post_batch(batch)
            except urllib.error.HTTPError as error:
                LOGGER.info("Rest Api is not reachable")
                response = json.loads(error.fp.read().decode('utf-8'))
                LOGGER.info(response['error']['title'])
                LOGGER.info(response['error']['message'])

    

class InvalidTransactions(ApiTxns):
    def __init__(self, payload,type):
        self.payload=payload
        self.signer = get_signer()
        self.data = {}
        self.invalidtype = invalidtype
        
    def get_batch_valinv_txns(self):
        """Setup method for posting batches and returning the 
           response
        """
        txns = [
            self.create_intkey_transaction("set",[],30, self.signer),
            self.create_intkey_transaction("set",[],30, self.signer),
            self.create_invalid_intkey_transaction("set",[],30, self.signer, self.invalidtype),
        ]
        self.data = self.get_txns_commit_data(txns,self.signer, self.data)
        return self.data

    def get_batch_invval_txns(self):
        """Setup method for posting batches and returning the 
           response
        """
        txns = [
            self.create_invalid_intkey_transaction("set",[],30, self.signer, self.invalidtype),
            self.create_intkey_transaction("set",[],30, self.signer),
            self.create_intkey_transaction("set",[],30, self.signer),
        ]
        self.data = self.get_txns_commit_data(txns,self.signer, self.data)
        return self.data
        
    def get_batch_invalid_txns(self):
        """Setup method for posting batches and returning the 
           response
        """  
          
        txns = [
                self.create_invalid_intkey_transaction("set",[],30, self.signer, self.invalidtype),
                self.create_invalid_intkey_transaction("set",[],30, self.signer, self.invalidtype),
                self.create_invalid_intkey_transaction("set",[],30, self.signer, self.invalidtype),
            ]

        self.data = self.get_txns_commit_data(txns,self.signer, self.data)
        return self.data
    
    def get_batch_valid_one_txns(self):
        """Setup method for posting batches and returning the 
           response
        """
        txns = [
            self.create_intkey_transaction("set",[],30, self.signer),
        ]
        self.data = self.get_txns_commit_data(txns,self.signer, self.data)
        return self.data
    
    def get_batch_valid_txns(self):
        """Setup method for posting batches and returning the 
           response
        """
        txns = [
            self.create_intkey_transaction("set",[],30, self.signer),
            self.create_intkey_transaction("set",[],30, self.signer),
            self.create_intkey_transaction("set",[],30, self.signer),
        ]
        self.data = self.get_txns_commit_data(txns,self.signer, self.data)
        return self.data
    
    def get_batch_same_txns(self):
        """Setup method for posting batches and returning the 
           response
        """
        txns = [
            self.create_intkey_same_transaction("set",[],30, self.signer),
            self.create_intkey_same_transaction("set",[],30, self.signer),
            self.create_intkey_same_transaction("set",[],30, self.signer),
        ]
        self.data = self.get_txns_commit_data(txns,self.signer, self.data)
        return self.data
    
    def get_batch_invalid_txns_fam_name(self):
        """Setup method for posting batches and returning the 
           response
        """  
          
        txns = [
                self.create_invalid_intkey_transaction("set",[],30, self.signer, self.invalidtype),
                self.create_invalid_intkey_transaction("set",[],30, self.signer, self.invalidtype),
                self.create_invalid_intkey_transaction("set",[],30, self.signer, self.invalidtype),
            ]

        self.data = self.get_txns_commit_data(txns,self.signer, self.data)
        return self.data
         
    def get_txns_commit_data(self, txns, signer, data):
        """Setup method for posting batches and returning the 
           response
        """
        expected_trxn_ids  = []
        expected_batch_ids = []
        expected_trxns  = {}
        expected_batches = []
        initial_batch_length = batch_count()
        initial_transaction_length = transaction_count()
    
        LOGGER.info("Creating intkey transactions with set operations")
        
        for txn in txns:
            dict = MessageToDict(
                    txn,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
    
            trxn_id = dict['header_signature']
            expected_trxn_ids.append(trxn_id)
        
        self.data['expected_trxn_ids'] = expected_trxn_ids
        expected_trxns['trxn_id'] = [dict['header_signature']]
        expected_trxns['payload'] = [dict['payload']]
        #print(expected_trxns['trxn_id'])
        print(expected_trxns['payload'])
        
    
        LOGGER.info("Creating batches for transactions 3trn/batch")
    
        batches = [create_batch(txns, signer)]
        for batch in batches:
            dict = MessageToDict(
                    batch,
                    including_default_value_fields=True,
                    preserving_proto_field_name=True)
    
            batch_id = dict['header_signature']
            expected_batches.append(batch_id)
        length_batches = len(expected_batches)
        length_transactions = len(expected_trxn_ids)
        data['expected_txns'] = expected_trxns['trxn_id'][::-1]
        
        post_batch_list = [BatchList(batches=[batch]).SerializeToString() for batch in batches]
        try:
            for batch in post_batch_list:
                response = post_batch(batch)
                batch_id = dict['header_signature']
                expected_batches.append(batch_id)
                self.data['response'] = response['data'][0]['status'] 
                print(response)
        except urllib.error.HTTPError as error:
            LOGGER.info("Rest Api is not reachable")
            json_data = json.loads(error.fp.read().decode('utf-8'))
            LOGGER.info(json_data['error']['title'])
            LOGGER.info(json_data['error']['message']) 
            LOGGER.info(json_data['error']['code'])             
            self.data['code'] = json_data['error']['code'] 

        self.state_addresses = [state['address'] for state in get_state_list()['data']]
        self.data['state_address'] = self.state_addresses
        self.data['initial_batch_length'] = initial_batch_length
        self.data['initial_trn_length'] = initial_transaction_length
        self.data['expected_batch_length'] = initial_batch_length + length_batches
        self.data['expected_trn_length'] = initial_transaction_length + length_transactions
        return self.data   
    
    def create_intkey_transaction(self, verb, deps, count, signer):
            words = random_word_list(count)
            name=random.choice(words)    
            payload = IntKeyPayload(
                verb=verb,name=name,value=21)

            addr = make_intkey_address(name)
            data = self.get_txns_data(addr,deps, payload)
            return data
    def create_intkey_same_transaction(self, verb, deps, count, signer):
            name='a'   
            payload = IntKeyPayload(
                verb=verb,name=name,value=1)
        
            addr = make_intkey_address(name)
            data = self.get_txns_data(addr,deps, payload)
            return data
        
    def create_invalid_intkey_transaction(self, verb, deps, count, signer, invalidtye):
        words = random_word_list(count)
        name=random.choice(words) 
        
        if invalidtye=="addr":  
            payload = IntKeyPayload(
                verb=verb,name=name,value=1)
            
            INVALID_INTKEY_ADDRESS_PREFIX = hashlib.sha512(
            'invalid'.encode('utf-8')).hexdigest()[0:6]
        
            addr = INVALID_INTKEY_ADDRESS_PREFIX + hashlib.sha512(
                name.encode('utf-8')).hexdigest()[-64:]
                
        if invalidtye=="invaddr":  
            payload = IntKeyPayload(
                verb=verb,name=name,value=1)
            
            INVALID_INTKEY_ADDRESS_PREFIX = hashlib.sha512(
            'invalid'.encode('utf-8')).hexdigest()[0:6]
        
            addr = INVALID_INTKEY_ADDRESS_PREFIX + hashlib.sha512(
                name.encode('utf-8')).hexdigest()[-62:]
            
        elif invalidtye=="min":   
            payload = IntKeyPayload(
                verb=verb,name=name,value=-1)
            addr = make_intkey_address(name)
        
        elif invalidtye=="str":    
            payload = IntKeyPayload(
                verb=verb,name=name,value="str")
            addr = make_intkey_address(name)
            
        elif invalidtye=="max":    
            payload = IntKeyPayload(
                verb=verb,name=name,value=4294967296)
            addr = make_intkey_address(name)
            
        elif invalidtye=="attr":    
            payload = IntKeyPayload(
                verb="verb",name=name,value=1)
            addr = make_intkey_address(name)
            
        elif invalidtye=="fn":    
            payload = IntKeyPayload(
                verb="verb",name=name,value=1)
            addr = make_intkey_address(name)
            header = TransactionHeader(
            signer_public_key=self.signer.get_public_key().as_hex(),
            family_name='abcd',
            family_version='1.0',
            inputs=[addr],
            outputs=[addr],
            dependencies=deps,
            payload_sha512=payload.sha512(),
            batcher_public_key=self.signer.get_public_key().as_hex())
    
            header_bytes = header.SerializeToString()
    
            signature = self.signer.sign(header_bytes)
    
            transaction = Transaction(
                header=header_bytes,
                payload=payload.to_cbor(),
                header_signature=signature)
            return transaction
            
        data = self.get_txns_data(addr,deps, payload)
        return data
   
    def get_txns_data(self, addr, deps, payload):
    
        header = TransactionHeader(
            signer_public_key=self.signer.get_public_key().as_hex(),
            family_name='intkey',
            family_version='1.0',
            inputs=[addr],
            outputs=[addr],
            dependencies=deps,
            payload_sha512=payload.sha512(),
            batcher_public_key=self.signer.get_public_key().as_hex())
    
        header_bytes = header.SerializeToString()
    
        signature = self.signer.sign(header_bytes)
    
        transaction = Transaction(
            header=header_bytes,
            payload=payload.to_cbor(),
            header_signature=signature)
    
        return transaction
    
        addr = make_intkey_address(name)
    
        header = TransactionHeader(
            signer_public_key=signer.get_public_key().as_hex(),
            family_name='intkey',
            family_version='1.0',
            inputs=[addr],
            outputs=[addr],
            dependencies=deps,
            payload_sha512=payload.sha512(),
            batcher_public_key=signer.get_public_key().as_hex())
    
        header_bytes = header.SerializeToString()
    
        signature = signer.sign(header_bytes)
    
        transaction = Transaction(
            header=header_bytes,
            payload=payload.to_cbor(),
            header_signature=signature)
    
        return transaction
    
    def create_payload(self):
        return
    
    def create_batch(self):
        transaction_signatures = [t.header_signature for t in transactions]
        header = BatchHeader(
            signer_public_key=signer.get_public_key().as_hex(),
            transaction_ids=transaction_signatures)
    
        header_bytes = header.SerializeToString()
    
        signature = signer.sign(header_bytes)
    
        batch = Batch(
            header=header_bytes,
            transactions=transactions,
            header_signature=signature)
    
        return batch
