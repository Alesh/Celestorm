import hashlib
from base64 import b64encode, b64decode
from dataclasses import astuple
from datetime import datetime

import pytest

from celestorm.encoding.errors import VerifyError, DeserializeError
from celestorm.samples.simldcls import Instruction
from tests.modcls import Account, Message
from tests.simple.impl.encoding import Package


def test_instruction():
    account = Account('01234567', 'Alesh')
    account_instruction = Instruction(account)
    assert account_instruction.oid == (Account, ('01234567',))
    serialized = account_instruction._serialize()
    assert serialized == b'[["Account"],0,["01234567","Alesh"]]'
    deserialized = Instruction._deserialize(serialized)
    assert deserialized.oid == account_instruction.oid
    assert deserialized.payload == account_instruction.payload

    message = Message('01234567', '2025-01-01T00:00:01', 'HNY!')
    create_message = Instruction(message)
    assert create_message.oid == (Message, ('01234567', '2025-01-01T00:00:01'))
    serialized = create_message._serialize()
    assert serialized == b'[["Message"],0,["01234567","2025-01-01T00:00:01","HNY!"]]'
    deserialized = Instruction._deserialize(serialized)
    assert deserialized.oid == create_message.oid
    assert deserialized.payload == create_message.payload
    assert deserialized.method == 'CREATE'

    update_message = Instruction(message, revision=1, message="Hi All!")
    assert update_message.oid == (Message, ('01234567', '2025-01-01T00:00:01'))
    serialized = update_message._serialize()
    assert serialized == b'[["Message","01234567","2025-01-01T00:00:01"],1,{"message":"Hi All!"}]'
    deserialized = Instruction._deserialize(serialized)
    assert deserialized.oid == update_message.oid == create_message.oid
    assert deserialized.payload == update_message.payload
    assert deserialized.revision == update_message.revision
    assert deserialized.method == 'UPDATE'

    delete_message = Instruction(message, revision=2)
    assert delete_message.oid == (Message, ('01234567', '2025-01-01T00:00:01'))
    serialized = delete_message._serialize()
    assert serialized == b'[["Message","01234567","2025-01-01T00:00:01"],2]'
    deserialized = Instruction._deserialize(serialized)
    assert deserialized.oid == delete_message.oid == create_message.oid
    assert deserialized.payload == delete_message.payload
    assert deserialized.revision == delete_message.revision
    assert deserialized.method == 'DELETE'


def test_package():
    addr = '01234567'
    serialized = Package.build([
        Instruction(Account(addr, 'Alesh')),
        Instruction(Message(addr, datetime.fromisoformat('2025-01-01T00:00:00'), 'HI!')),
        Instruction(Message(addr, datetime.fromisoformat('2025-01-01T00:00:01'), 'HNY!')),
    ])

    assert hashlib.sha256(serialized).hexdigest() == '1bd4c970c7c1f944e35e2b0ba41aa8d3600f68cb88eec67265bae878542f10f1'
    restored = Package(bytes(serialized))
    assert serialized == restored

    assert [astuple(instruction.payload) for instruction in Package(bytes(serialized)).deserialize()] == [
        ('01234567', 'Alesh'),
        ('01234567', datetime(2025, 1, 1, 0, 0), 'HI!'),
        ('01234567', datetime(2025, 1, 1, 0, 0, 1), 'HNY!')
    ]


try:
    import celestorm.encoding.protocols
    from celestorm import encoding
    from nacl.exceptions import BadSignatureError
    from nacl.signing import SigningKey, VerifyKey


    class Signer(encoding.protocols.Signer):
        """ Package signer """
        sign_size = 64

        def __init__(self, key: SigningKey | VerifyKey):
            if not isinstance(key, (SigningKey, VerifyKey)):
                raise TypeError("key must be SigningKey or VerifyKey")
            self._key = key if isinstance(key, SigningKey) else None
            self._pub = key.verify_key if isinstance(key, SigningKey) else key

        def sign(self, message: bytes) -> bytes:
            """ Signs the message and returns the signature. """
            if self._key is None:
                raise RuntimeError("Cannot sign. Signer is public.")
            signed = self._key.sign(message)
            return signed.signature

        def verify(self, message: bytes, signature: bytes) -> bool:
            """ Verifies the signature. """
            try:
                self._pub.verify(message, signature)
                return True
            except BadSignatureError:
                return False


    def test_package_seal_verify():
        key = SigningKey(seed=b'0123456789ABCDEF0123456789ABCDEF')
        addr = b64encode(bytes(key.verify_key)).decode('ascii')

        serialized = Package.build([
            Instruction(Account(addr, 'Alesh')),
            Instruction(Message(addr, datetime.fromisoformat('2025-01-01T00:00:00'), 'HI!')),
            Instruction(Message(addr, datetime.fromisoformat('2025-01-01T00:00:01'), 'HNY!')),
        ], signer=Signer(key))
        assert hashlib.sha256(
            serialized).hexdigest() == 'a33c59ca2dfd7aced7164cc1270912e9e8902382c3e76f3516adaa5b734128b6'

        restored = Package(bytes(serialized))
        assert serialized == restored
        package = Package(bytes(serialized))

        deserialized = [
            astuple(instruction.payload)
            for instruction in package.deserialize(
                signer=Signer(VerifyKey(b64decode(addr.encode('ascii')))))
        ]
        assert deserialized == [
            (addr, 'Alesh'),
            (addr, datetime(2025, 1, 1, 0, 0), 'HI!'),
            (addr, datetime(2025, 1, 1, 0, 0, 1), 'HNY!')
        ]

        assert serialized.signed
        assert package.verify(signer=Signer(VerifyKey(b64decode(addr.encode('ascii')))))
        assert not package.verify(signer=Signer(VerifyKey(b'XXX3456789ABCDEF0123456789ABCXXX')))

        with pytest.raises(VerifyError, match="Wrong package hash"):
            broken_package = Package(serialized[:21] + b'XXX' + serialized[24:])
            tuple(broken_package.deserialize(signer=Signer(VerifyKey(b64decode(addr.encode('ascii'))))))

        with pytest.raises(DeserializeError, match="Cannot deserialize instruction"):
            broken_package = Package(serialized[:20] + b'XXX' + serialized[23:])
            tuple(broken_package.deserialize(signer=Signer(VerifyKey(b64decode(addr.encode('ascii'))))))

except ImportError:
    pass
