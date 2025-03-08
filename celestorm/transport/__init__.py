"""
The *celestorm.transport* module contains generic abstract classes and
protocols for interacting with the distributed system's network. Their concrete
implementations enable the reception and transmission of instruction packages
over the network. The module's components are typed with the distributed system's
object identifier (U).
"""
import typing as t
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from celestorm.encoding import Package
from celestorm.encoding.protocols import Instruction
from .errors import ConnectionClosed
from .protocols import Connection, Transmitter

__all__ = ('Transport',)


class Transport[U](ABC):
    """ A generic abstract base class with partial implementation that defines
    the transport layer for receiving and sending instruction packages over the
    distributed system's network.
    """

    def __init__(self):
        self._connections = set()  # type: set[Connection[U]]

    @property
    def active(self) -> bool:
        """ Returns `True` if there are active network connections. """
        return len(self._connections) > 0

    def close(self):
        """ Closes all active network connections. """
        for connection in self._connections:
            connection.close()

    def transmitter(self, *args: t.Any, **kwargs: t.Any) -> AbstractAsyncContextManager['Transmitter[U]', bool]:
        """ Returns a context manager for accumulating instructions.
        Upon entering the context, a connection is established, and an object
        implementing the ``celestorm.transport.protocols.Transmitter`` protocol
        is returned, accepting instructions. Upon exiting the context,
        the collected instructions are automatically packed into a package
        and sent over the network.

        Args:
            args: Reserved positional arguments.
            kwargs: Reserved named arguments.
        """
        instructions: list[Instruction[U]] = []

        class _Transmitter:
            sync_round: int | None = None
            sent_count: int = 0

            def __call__(self, instruction: Instruction[U]):
                instructions.append(instruction)

        @asynccontextmanager
        async def enter_transmitter_context():
            packager = self._packager_factory(*args, **kwargs)
            connection = self._connection_factory(*args, **kwargs)
            assert isinstance(connection, Connection)
            try:
                self._connections.add(connection)
                await connection.open_connection(*args, **kwargs)
                transmitter = _Transmitter()
                yield transmitter
                package = packager(instructions)
                transmitter.sync_round = await connection.send_package(package, *args, **kwargs)
                transmitter.sent_count = len(instructions)
            finally:
                self._connections.remove(connection)
                await connection.close_connection()

        return enter_transmitter_context()

    def receiver(self, from_round: int, *args: t.Any, **kwargs: t.Any) \
            -> AbstractAsyncContextManager[AsyncIterator[tuple[int, Package[U]]], bool]:
        """ Returns a context manager for receiving instructions. Upon entering
        the context, a connection is established, and an async iterator
        of instructions is returned.

        Args:
            from_round: The sync round number from which instruction retrieval begins.
            args: Reserved positional arguments.
            kwargs: Reserved named arguments.

        Returns:
            An async iterator yielding a tuple of the sync round and
            the corresponding instruction package.
        """

        async def _receiver(connection: Connection[U]):
            nonlocal from_round, args, kwargs
            try:
                async for sync_round, package, args_ in connection.recv_packages(from_round, *args, **kwargs):
                    packager = self._packager_factory(*args_, **kwargs)
                    yield sync_round, packager(package)
            except ConnectionClosed:
                pass

        @asynccontextmanager
        async def enter_receiver_context():
            connection = self._connection_factory(*args, **kwargs)
            assert isinstance(connection, Connection)
            try:
                self._connections.add(connection)
                await connection.open_connection(*args, **kwargs)
                yield _receiver(connection)
            finally:
                self._connections.remove(connection)
                await connection.close_connection()

        return enter_receiver_context()

    @abstractmethod
    def _packager_factory(self, *args: t.Any, **kwargs: t.Any) \
            -> type[Package[U]] | t.Callable[[bytes | t.Sequence[Instruction[U]]], Package[U]]:
        """ Must return a class implementing the instruction package
        ``celestorm.encoding.Package`` or a function creating its instance.

        Args:
            args: Reserved positional arguments.
            kwargs: Reserved named arguments.
        """

    @abstractmethod
    def _connection_factory(self, *args: t.Any, **kwargs: t.Any) -> Connection[U]:
        """ Must return a class implementing the network interaction protocol
        ``celestorm.transport.protocols.Connection``.

        Args:
            args: Reserved positional arguments.
            kwargs: Reserved named arguments.
        """
