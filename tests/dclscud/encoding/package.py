import hashlib
import typing as t
from abc import ABC
from io import BytesIO
from typing import AsyncIterator

import celestorm.encoding
import celestorm.encoding.protocols
from celestorm.encoding.errors import DeserializeError, SerializeError, VerifyError
from celestorm.utils import varint
from .instruction import Instruction, OID


class Package(celestorm.encoding.Package[OID], ABC):
    """ Sample package """

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

    def _deserialize_instruction(self, instruction: bytes):
        return Instruction.deserialize(instruction)
