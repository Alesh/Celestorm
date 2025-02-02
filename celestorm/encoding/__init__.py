"""
The `celestorm.encoding` module contains generic abstract classes and protocols
for data binding and encoding. The module's components are typed with the
distributed system's object identifier (U).
"""
import typing as t
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from .errors import DeserializeError, EncodingError, VerifyError
from .protocols import Instruction

__all__ = ('Package',)


class Package[U](bytes, ABC):
    """ A generic abstract base class with partial implementation that defines
    an instruction package. An instance of this class stores a set of instructions
    packed into a byte string.

    Args:
        instructions: Instructions to serialize and pack.

    Raises:
        SerializeError: Raised when an error occurs during package creation.
    """
    version: t.ClassVar[int] = 1

    if t.TYPE_CHECKING:
        def __init__(self, instructions: bytes | t.Sequence[Instruction[U]]): ...

    def __new__(cls, instructions: bytes | t.Sequence[Instruction[U]]) -> 'Package[U]':
        if isinstance(instructions, bytes):
            return super().__new__(cls, instructions)
        assert all(isinstance(instruction, Instruction) for instruction in instructions), \
            "All instructions must be implements protocol `Instruction`"
        return cls._create_from(instructions)

    @property
    def body(self) -> bytes:
        """ Returns the byte representation of the package's data body,
        suitable for hashing and signing. """
        pos, size = self._get_body_slice()
        return self[pos:][:size]

    @property
    def digest(self) -> bytes | None:
        """ Returns the byte representation of the package's data hash,
        if the package is hashed. """
        pos, size = self._get_digest_slice()
        if pos >= 0:
            return self[pos:][:size]

    @property
    def signature(self) -> bytes | None:
        """ Returns the byte representation of the package's digital signature,
        if the package is signed. """
        pos, size = self._get_signature_slice()
        if pos >= 0:
            return self[pos:][:size]

    async def deserialize(self, *args: t.Any, **kwargs: t.Any) -> AsyncIterator[Instruction[U]]:
        """ Performs deserialization of instructions from the package.

        Args:
            args: Reserved positional arguments.
            kwargs: Reserved named arguments.

        Returns:
            An async iterator of deserialized instructions.

        Raises:
            DeserializeError: Raised on deserialization error.
            VerifyError: Raised on integrity verification failure.
        """
        try:
            async for serialized in self._serialized_instructions(*args, **kwargs):
                yield self._deserialize_instruction(serialized)
        except Exception as exc:
            if not isinstance(exc, (DeserializeError, VerifyError)):
                raise DeserializeError(f"Cannot deserialize package; {exc}") from exc
            raise exc

    @abstractmethod
    def _get_body_slice(self) -> tuple[int, int]:
        """ Returns the position and length of the package's main body. """

    @abstractmethod
    def _get_digest_slice(self) -> tuple[int, int]:
        """ Returns the position and length of the byte representation of
        the package's data hash. """

    @abstractmethod
    def _get_signature_slice(self) -> tuple[int, int]:
        """ Returns the position and length of the byte representation of
        the package's signature. """

    @classmethod
    @abstractmethod
    def _create_from(cls, instructions: t.Sequence[Instruction[U]]) -> 'Package[U]':
        """ Creates a package from a set of instructions.

        Args:
            instructions: Instructions to pack.

        Raises:
            EncodingError: Raised on serialization error.
        """
        method = f'{cls.__module__}.{cls.__name__}._create_from'
        raise NotImplementedError(f"You can't use a non-implemented method `{method}` here.")

    @abstractmethod
    def _serialized_instructions(self, *args: t.Any, **kwargs: t.Any) -> AsyncIterator[bytes]:
        """ Creates and returns an async iterator of the package's serialized instructions.

        Args:
            args: Reserved positional arguments.
            kwargs: Reserved named arguments.

        Returns:
            An async iterator of serialized instructions.

        Raises:
            ValueError: Raised on package parsing error.
            VerifyError: Raised on integrity verification failure.
        """

    @abstractmethod
    def _deserialize_instruction(self, instruction: bytes) -> Instruction[U]:
        """ Deserializes an instruction.

        Args:
            instruction: The byte-represented instruction to deserialize.

        Исключения:
            DeserializeError: Raised on deserialization error.
        """
