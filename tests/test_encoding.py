import hashlib
from base64 import b64encode, b64decode
from dataclasses import astuple
from datetime import datetime

import pytest

from celestorm.encoding.errors import VerifyError, DeserializeError
from tests.impl import encoding
from tests.impl.dclscud import Instruction, Package
from tests.models import Account, Message

if encoding.SIGNING_SUPPORTED:
    from nacl.signing import SigningKey, VerifyKey


def test_instruction():
    account = Account('01234567', 'Alesh')
    account_instruction = Instruction(account)
    assert account_instruction.oid == (Account, ('01234567',))
    serialized = account_instruction.serialize()
    assert serialized == b'[["Account"],0,["01234567","Alesh"]]'
    deserialized = Instruction.deserialize(serialized)
    assert deserialized.oid == account_instruction.oid
    assert deserialized.payload == account_instruction.payload

    message = Message('01234567', '2025-01-01T00:00:01', 'HNY!')
    create_message = Instruction(message)
    assert create_message.oid == (Message, ('01234567', '2025-01-01T00:00:01'))
    serialized = create_message.serialize()
    assert serialized == b'[["Message"],0,["01234567","2025-01-01T00:00:01","HNY!"]]'
    deserialized = Instruction.deserialize(serialized)
    assert deserialized.oid == create_message.oid
    assert deserialized.payload == create_message.payload
    assert deserialized.method == 'CREATE'

    update_message = Instruction(message, revision=1, message="Hi All!")
    assert update_message.oid == (Message, ('01234567', '2025-01-01T00:00:01'))
    serialized = update_message.serialize()
    assert serialized == b'[["Message","01234567","2025-01-01T00:00:01"],1,{"message":"Hi All!"}]'
    deserialized = Instruction.deserialize(serialized)
    assert deserialized.oid == update_message.oid == create_message.oid
    assert deserialized.payload == update_message.payload
    assert deserialized.revision == update_message.revision
    assert deserialized.method == 'UPDATE'

    delete_message = Instruction(message, revision=2)
    assert delete_message.oid == (Message, ('01234567', '2025-01-01T00:00:01'))
    serialized = delete_message.serialize()
    assert serialized == b'[["Message","01234567","2025-01-01T00:00:01"],2]'
    deserialized = Instruction.deserialize(serialized)
    assert deserialized.oid == delete_message.oid == create_message.oid
    assert deserialized.payload == delete_message.payload
    assert deserialized.revision == delete_message.revision
    assert deserialized.method == 'DELETE'


async def test_package():
    addr = '01234567'
    serialized = Package([
        Instruction(Account(addr, 'Alesh')),
        Instruction(Message(addr, datetime.fromisoformat('2025-01-01T00:00:00'), 'HI!')),
        Instruction(Message(addr, datetime.fromisoformat('2025-01-01T00:00:01'), 'HNY!')),
    ])

    assert len(serialized.digest) == 32
    assert hashlib.sha256(serialized).hexdigest() == '78a36de208bfdf6cd19259ec18c430b945b3c2148c7413e2946c9f1e3f315b55'
    assert hashlib.sha256(serialized.body).digest() == serialized.digest
    restored = Package(bytes(serialized))
    assert serialized == restored

    assert [astuple(instruction.payload) async for instruction in Package(bytes(serialized)).deserialize()] == [
        ('01234567', 'Alesh'),
        ('01234567', datetime(2025, 1, 1, 0, 0), 'HI!'),
        ('01234567', datetime(2025, 1, 1, 0, 0, 1), 'HNY!')
    ]


async def test_package_seal_verify():
    if encoding.SIGNING_SUPPORTED:
        key = SigningKey(seed=b'0123456789ABCDEF0123456789ABCDEF')
        addr = b64encode(bytes(key.verify_key)).decode('ascii')

        serialized = Package([
            Instruction(Account(addr, 'Alesh')),
            Instruction(Message(addr, datetime.fromisoformat('2025-01-01T00:00:00'), 'HI!')),
            Instruction(Message(addr, datetime.fromisoformat('2025-01-01T00:00:01'), 'HNY!')),
        ])

        assert serialized.signature is None
        signed = serialized.sign(key)
        assert len(signed.signature) == 64

        assert (hashlib.sha256(signed).hexdigest() ==
                'cd2ee4280ab99bd210aea2b84c16beee7e4c2e7ba5b585b929fab662cfa38814')
        assert signed.verify(VerifyKey(b64decode(addr.encode('ascii'))))

        restored = Package(bytes(signed))
        assert serialized.body == restored.body
        assert serialized.digest == restored.digest
        assert signed.signature == restored.signature

        deserialized = [astuple(instruction.payload) async for instruction in restored.deserialize()]
        assert deserialized == [
            (addr, 'Alesh'),
            (addr, datetime(2025, 1, 1, 0, 0), 'HI!'),
            (addr, datetime(2025, 1, 1, 0, 0, 1), 'HNY!')
        ]

        assert restored.verify(VerifyKey(b64decode(addr.encode('ascii'))))
        assert not restored.verify(VerifyKey(b'XXX3456789ABCDEF0123456789ABCXXX'))

        with pytest.raises(VerifyError, match="Wrong package hash"):
            broken_package = Package(serialized[:21] + b'XXX' + serialized[24:])
            tuple([i async for i in broken_package.deserialize()])

        with pytest.raises(DeserializeError, match="Cannot deserialize instruction"):
            broken_package = Package(serialized[:20] + b'XXX' + serialized[23:])
            tuple([i async for i in broken_package.deserialize()])
