import typing as t
from abc import abstractmethod, ABC
from collections.abc import AsyncIterator

from celestorm.encoding import Instruction, Package


class Connection[U](ABC):
    """ This is an abstract base class that defines a partially implemented
    interface for receiving and transmitting packets from a supporting platform.
    """

    def __init__(self):
        self.__connected = False

    @property
    def connected(self) -> bool:
        """ Returns True if the connection has been established. """
        return self.__connected

    async def send_instructions(self, instructions: t.Sequence[Instruction[U]],
                                *args: t.Any, **kwargs: t.Any) -> int:
        """ Method serializes instructions in a package, and then sends them to the
        supporting platform.

        Args:
            instructions: Instructions to send.
            args: Arguments reserved for use in implementation.
            kwargs: Keyword arguments reserved for use in implementation.

        Returns:
            Synchronization round in which a instruction package was accepted by
            the supporting platform.

        Raises:
            ConnectionError: If error occurred while sending package.
        """
        if not self.connected:
            raise ConnectionError("Not connected")
        packager = self._packager_factory(*args, **kwargs)
        package = packager(instructions)
        return await self._send_package(package, *args, **kwargs)

    async def recv_instructions(self, after_sync_round: int,
                                *args: t.Any, **kwargs: t.Any) -> AsyncIterator[tuple[int, Package[U]]]:
        """ Method makes an asynchronous iterator that yields instructions
        coming from the supporting platform.

        Args:
            after_sync_round: The sync round number after which to receive instructions.
            args: Arguments reserved for use in implementation.
            kwargs: Keyword arguments reserved for use in implementation.

        Returns:
            An asynchronous iterator that returns a tuple consisting of the
            current sync round, the received package of serialized instructions
            and a tuple with additional information useful for recognizing the package.

        Raises:
            ConnectionError: If error occurred while receiving packages.
        """
        if not self.connected:
            raise ConnectionError("Not connected")
        async for sync_round, package, args in self._recv_packages(after_sync_round, *args, **kwargs):
            packager = self._packager_factory(*args, **kwargs)
            yield sync_round, packager(package)

    async def _open_connection(self) -> None:
        """ This method should be overridden by subclasses to establish
        connection to the supporting platform.
        """
        self.__connected = True

    async def _close_connection(self) -> None:
        """ This method should be overridden by subclasses to close
        connection to the supporting platform.
        """
        self.__connected = False

    @abstractmethod
    def close(self):
        """ Close this connection.
        After calling this method, sending packets should fail with
        a `ConnectionError` error, and the receiving packet iterator should exit.
        """

    @abstractmethod
    def _packager_factory(self, *args: t.Any, **kwargs: t.Any) \
            -> type[Package[U]] | t.Callable[[bytes | t.Sequence[Instruction[U]]], Package[U]]:
        """ This method must return callable returned a concrete class that implements
        a serialized instruction package, or a callable that returns such an instance.

        Args:
            args: Arguments reserved for use in implementation.
            kwargs: Keyword arguments reserved for use in implementation.
        """

    @abstractmethod
    def _send_package(self, package: Package[U],
                      *args: t.Any, **kwargs: t.Any) -> t.Coroutine[t.Any, t.Any, int]:
        """ This method must send a package of instructions to the supporting platform.

        Args:
            package: The serialized instruction package as bytestring.
            args: Arguments reserved for use in implementation.
            kwargs: Keyword arguments reserved for use in implementation.

        Returns:
            Synchronization round in which a package was accepted by
            the supporting platform.

        Raises:
            ConnectionError: If error occurred while sending package.
        """

    @abstractmethod
    def _recv_packages(self, after_sync_round: int,
                       *args: t.Any, **kwargs: t.Any) -> AsyncIterator[tuple[int, bytes, tuple[t.Any, ...]]]:
        """ This method must create an asynchronous iterator that yields BLOB
        with serialized instruction packets coming from the supporting platform.

        Args:
            after_sync_round: The sync round number after which to receive instructions.
            *args: Some parameters reserved for use in superclasses.
            **kwargs: Some parameters reserved for use in superclasses.

        Returns:
            An asynchronous iterator that returns a tuple consisting of the
            current sync round, the received package of serialized instructions
            and a tuple with additional information useful for recognizing
            the package.

        Raises:
            ConnectionError: If error occurred while receiving packages.
        """
