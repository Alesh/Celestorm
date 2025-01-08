"""
In order for instructions to be transmitted between nodes in a distributed system,
they must be serialized, “sealed” with a hash, and, if necessary, signed.
This prevents data from being tampered with or corrupted during data transmission.
Another important point is that one block of instructions must be executed
consistently and in one transactional context.
All this is solved with packaging.
"""

import hashlib
import typing as t
from abc import abstractmethod, ABC
from io import BytesIO

from . import varint
from .errors import SerializeError, DeserializeError, VerifyError
from .instruction import Instruction
from .protocols import Hasher, Signer


class Package[U](bytes, ABC):
    """
    Abstract base class representing a package of serialized instructions.

    This class is designed to store a set of instructions that will be converted
    to a string of bytes, hashed, and possibly signed with. This approach allows
    you to ensure the security of data transmission in a distributed system.

    To define how to deserialize the packet and into which instructions,
    you need to override the protected method :meth:`._instruction_deserializer`.

    Args:
        instructions: instructions to serialize.
        hasher: hashing object to use; defaults sha256

    Raises:
        `SerializeError`: Raised when an instruction packet cannot be created.
    """
    version: t.ClassVar[int] = 1

    if t.TYPE_CHECKING:
        def __init__(self, instructions: bytes | t.Sequence[Instruction[U]], hasher: Hasher = None): ...

    def __new__(cls, instructions: bytes | t.Sequence[Instruction[U]], hasher: Hasher = None) -> 'Package[U]':
        if isinstance(instructions, bytes):
            return super().__new__(cls, instructions)
        return cls.build(instructions, hasher=hasher)

    @property
    def signed(self) -> bool:
        """ true if a package is signed.  """
        return bool(self[0] & 0b10000000)

    @classmethod
    def build(cls, instructions: t.Sequence[Instruction[U]], *args,
              hasher: Hasher = None, signer: Signer = None) -> 'Package[U]':
        """ Create a package from instructions.

        Args:
            instructions: The instructions to package.
            hasher: An object with `Hasher` protocol that used to make hash of a package; default sha256.
            signer: An object with `Signer` protocol that can be used for signing a package.

        Raises:
            `SerializeError`: Raised when an instruction packet cannot be created.
        """
        assert cls.version < 0b01111111
        if len(instructions) > 0xFFFF:
            raise SerializeError("Too many instructions; maximum package size is 65535")
        hasher = hasher or hashlib.sha256()
        result = (cls.version | 0b10000000 if signer is not None else cls.version).to_bytes(1)
        result += len(instructions).to_bytes(2, byteorder='little')
        hasher.update(result)
        try:
            for instruction in instructions:
                serialized = instruction._serialize()
                chunk = varint.encode(len(serialized)) + serialized
                hasher.update(chunk)
                result += chunk
            hash = hasher.digest()
            result += hash
            if signer is not None:
                result += signer.sign(hash)
            return cls(result)
        except Exception as exc:
            raise SerializeError(f"Serialization fail, because '{exc}'") from exc

    def deserialize(self, hasher: Hasher = None, signer: Signer = None) -> t.Iterable[Instruction[U]]:
        """ Deserializes instructions from this package.

        Args:
            hasher: An object with `Hasher` protocol that used to make hash of a package; default sha256.
            signer: An object with `Signer` protocol that can be used for signing a package.

        Returns:
            Iterable collection of deserialized instructions.

        Raises:
            DeserializeError: if the package could not be deserialized.
            VerifyError: if the package cannot be verified.
        """
        stream = BytesIO(self)
        hasher = hasher or hashlib.sha256()
        deserializer = self._instruction_deserializer()
        try:

            def iter_(package_size) -> t.Iterable[Instruction[U]]:
                while package_size:
                    try:
                        size, chunk = varint.decode_stream_ex(stream)
                        hasher.update(chunk)
                        chunk = stream.read(size)
                        hasher.update(chunk)
                        yield deserializer(chunk)
                        package_size -= 1
                    except EOFError:
                        raise DeserializeError("Wrong package size")
                hash = stream.read(hasher.digest_size)
                if hash != hasher.digest():
                    raise VerifyError("Wrong package hash")
                if signer is not None:
                    signature = stream.read(signer.sign_size)
                    if len(signature) != signer.sign_size or not signer.verify(hash, signature):
                        raise VerifyError("Wrong package signature")

            chunk = stream.read(1)
            hasher.update(chunk)
            version = int.from_bytes(chunk) & 0b0111111
            if version != self.version:
                raise DeserializeError("Wrong package version")
            chunk = stream.read(2)
            hasher.update(chunk)
            return iter_(int.from_bytes(chunk, byteorder='little'))

        except EOFError:
            raise DeserializeError("Wrong package header")
        except Exception as exc:
            if not isinstance(exc, (DeserializeError, VerifyError)):
                raise DeserializeError(f"Deserialization fail, because '{exc}'")
            raise exc

    def verify(self, signer: Signer, hasher: Hasher = None) -> bool:
        """ Verify a package.

        Args:
            signer: An object with `Signer` protocol that can be used check signature of a package.
            hasher: An object with `Hasher` protocol that used to check hash of a package; default sha256

        Raises:
            VerifyError: Raised if the value is wrong or cannot be verified.
        """
        try:
            return bool([_ for _ in self.deserialize(hasher, signer)])
        except (DeserializeError, VerifyError):
            return False

    @abstractmethod
    def _instruction_deserializer(self) -> t.Callable[[bytes], Instruction[U]]:
        """ This method must return an instruction deserializer. """
