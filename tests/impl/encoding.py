import hashlib
import typing as t
from abc import ABC, abstractmethod
from datetime import datetime
from io import BytesIO
from typing import AsyncIterator

import celestorm.encoding
import celestorm.encoding.protocols
from celestorm.encoding.protocols import Entity
from celestorm.encoding.errors import DeserializeError, SerializeError, VerifyError, SignError
from celestorm.utils import varint

try:
    from nacl.exceptions import BadSignatureError
    from nacl.signing import SigningKey, VerifyKey

    SIGNING_SUPPORTED = True
except ImportError:
    SIGNING_SUPPORTED = False
    raise

type OID = tuple[type, type[t.Any, ...]]


def default_encoder(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class Instruction(celestorm.encoding.protocols.Instruction[OID]):
    """ Sample instruction """

    def __init__(self, entity: Entity[OID], revision: int = 0, **data: t.Any):
        if not isinstance(entity, Entity):
            raise TypeError("Parameter `entity` must support protocol `Entity`")
        if not (isinstance(revision, int) and revision >= 0):
            raise ValueError(f"Parameter `revision` must be an integer and >= 0")
        self.__oid = entity.oid
        self.__revision = revision
        if revision:
            if data:
                self.__payload = data
            else:
                self.__payload = None
        else:
            self.__payload = entity

    @property
    def oid(self) -> OID:
        """ Object ID """
        return self.__oid

    @property
    def payload(self) -> Entity[OID] | dict[str, t.Any]:
        """ Instruction payload. """
        return self.__payload

    @property
    def revision(self) -> int:
        """ Revision number """
        return self.__revision

    @property
    def method(self) -> t.Literal['CREATE', 'UPDATE', 'DELETE']:
        """ Method of instruction being processed. """
        if self.revision:
            if self.payload is not None:
                method = 'UPDATE'
            else:
                method = 'DELETE'
        else:
            method = 'CREATE'
        return t.cast(t.Literal['CREATE', 'UPDATE', 'DELETE'], method)

    @abstractmethod
    def serialize(self) -> bytes:
        """ Method must serialize instruction to bytestring.  """

    @classmethod
    @abstractmethod
    def deserialize(cls, data: bytes) -> 'Instruction':
        """ Method must deserialize instruction from bytestring.  """
        method = f'{cls.__module__}.{cls.__name__}._deserialize'
        raise NotImplementedError(f"You can't use a non-implemented method `{method}` here.")


class Package(celestorm.encoding.Package[OID], ABC):
    """ Sample package """

    if SIGNING_SUPPORTED:

        def sign(self, key: SigningKey) -> 'Package':
            if not self.digest:
                raise SignError("Digest not specified; cannot sign")
            if self.signature:
                raise SignError("Package already signed")
            signed = key.sign(self.digest)
            return Package((self[0] | 0b10000000).to_bytes() + self[1:] + signed.signature)

        def verify(self, key: VerifyKey) -> bool:
            if not self.signature:
                raise SignError("Package isn't signed")
            try:
                key.verify(self.digest, self.signature)
                return True
            except BadSignatureError:
                return False

    def _get_body_slice(self) -> tuple[int, int]:
        size, _ = self._get_digest_slice()
        if size < 0:
            size = len(self)
        return 3, size - 3

    def _get_digest_slice(self) -> tuple[int, int]:
        if self[0] & 0b01000000:
            pos = len(self) - hashlib.sha256().digest_size
            if self[0] & 0b10000000:
                pos -= 64
            return pos, hashlib.sha256().digest_size
        return -1, 0

    def _get_signature_slice(self) -> tuple[int, int]:
        if self[0] & 0b10000000:
            pos = len(self) - 64
            return pos, 64
        return -1, 0

    @classmethod
    def _create_from(cls, instructions: t.Sequence[Instruction]) -> 'Package':
        assert cls.version < 0b00111111
        if len(instructions) > 0xFFFF:
            raise SerializeError("Too many instructions; maximum package size is 65535")
        result = cls.version.to_bytes(1)
        result += len(instructions).to_bytes(2, byteorder='little')
        hasher = hashlib.sha256()
        try:
            for instruction in instructions:
                serialized = instruction.serialize()
                chunk = varint.encode(len(serialized)) + serialized
                hasher.update(chunk)
                result += chunk
            hash = hasher.digest()
            result = (result[0] | 0b01000000).to_bytes() + result[1:] + hash
            return cls(result)
        except Exception as exc:
            raise SerializeError(f"Serialization fail, because '{exc}'") from exc

    async def _serialized_instructions(self, *args: t.Any, **kwargs: t.Any) -> AsyncIterator[bytes]:
        stream = BytesIO(self)
        chunk = stream.read(1)
        version = int.from_bytes(chunk) & 0b00111111
        if version != self.version:
            raise DeserializeError("Wrong package version")
        chunk = stream.read(2)
        package_size = int.from_bytes(chunk, byteorder='little')
        hasher = hashlib.sha256()
        while package_size:
            try:
                size, chunk = varint.decode_stream_ex(stream)
                hasher.update(chunk)
                chunk = stream.read(size)
                hasher.update(chunk)
                yield chunk
                package_size -= 1
            except EOFError:
                raise DeserializeError("Wrong package size")
        hash = stream.read(hasher.digest_size)
        if hash != hasher.digest():
            raise VerifyError("Wrong package hash")
