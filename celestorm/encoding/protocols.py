"""
This module defines protocols used to encode data. It will provide type
hints in Python and make interfaces easier to understand for implementations.
"""
import typing as t


@t.runtime_checkable
class Entity[U](t.Protocol):
    """
    Protocol defining an entity with a unique identifier.

    This protocol requires an implementation to provide a unique object
    identifier (OID) through the `oid` property.

    Type Parameters:
        U: The type of the unique object identifier.
    """

    @property
    def oid(self) -> U:
        """ Unique object identifier.

        This property should return a unique identifier for the entity.
        The specific implementation is deferred to the concrete class.
        """


@t.runtime_checkable
class Hasher(t.Protocol):
    """ Protocol for a hashing object.

    This protocol defines the methods and properties required for a
    hashing implementation, including the ability to update the hash
    with new data and retrieve the resulting digest.

    Attributes:
        digest_size: The size of the resulting hash in bytes.
    """

    digest_size: t.ClassVar[int]

    def update(self, data: bytes):
        """ Update the hash object with the given bytes.

        Repeated calls to this method are equivalent to a single call
        with the concatenation of all arguments.

        Args:
            data: The data to be added to the hash.
        """

    def digest(self) -> bytes:
        """ Return the current hash digest.

        This method returns the digest of the bytes passed to the
        `update()` method so far as a bytes object.

        Returns:
            The resulting hash digest.
        """


@t.runtime_checkable
class Signer(t.Protocol):
    """ Protocol for a signing object.

    This protocol defines the methods and properties required for a
    signing implementation, including the ability to sign messages
    and verify signatures.

    Attributes:
        sign_size: The size of the signature in bytes.
    """
    sign_size: t.ClassVar[int]

    def sign(self, message: bytes) -> bytes:
        """ Sign the given message.

        This method takes a message as input and returns the corresponding
        signature.

        Args:
            message: The message to be signed.

        Returns:
            The generated signature for the message.
        """

    def verify(self, message: bytes, signature: bytes) -> bool:
        """ Verify the signature of a given message.

        This method checks if the provided signature is valid for the
        given message.

        Args:
            message: The message whose signature is to be verified.
            signature: The signature to verify against the message.

        Returns:
            True if the signature is valid, False otherwise.
        """
