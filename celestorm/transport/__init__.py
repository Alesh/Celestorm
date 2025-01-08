import typing as t
from abc import abstractmethod, ABC
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from celestorm.encoding import Instruction, Package
from .connection import Connection


class Transmitter[U]:
    """ Instruction transmitter.

    An instance of this class is responsible for collecting instructions into
    a package and then sending them to the supporting platform.
    """

    def __init__(self, connection: Connection[U]):
        self._connection = connection
        self._instructions: list[Instruction] = []
        self.__sync_round = None  # type: int |None

    def __call__(self, instruction: Instruction[U]):
        self._instructions.append(instruction)

    @property
    def sync_round(self) -> int | None:
        """ The number of the synchronization round in which the transmitted
        packet was accepted by the platform. Until the successful sending of
        the packet is completed, the property will contain 0.
        """
        return self.__sync_round

    @property
    def sent_count(self) -> int:
        """ The number of instructions sent in the packet. """
        return len(self._instructions) if self.sync_round is not None else 0

    async def send_instructions(self, *args: t.Any, **kwargs: t.Any):
        """ Sends instructions to the platform.

        Args:
            args: Arguments reserved for use in implementation.
            kwargs: Keyword arguments reserved for use in implementation.
        """
        self.__sync_round = await self._connection.send_instructions(self._instructions, *args, **kwargs)


class Transport[U](ABC):
    """ Transport for interacting with the platform.

    This class encapsulates and coordinates the methods responsible for exchanging
    data with the supporting platform. The concrete implementation of the connection
    to the platform must be implemented in a descendant of the :class:`~celestorm.transport.Connection` class
    and associated with the transport by overriding the protected method :meth:`._connection_factory`.
    """

    def __init__(self):
        self._connections = list()  # type: list[Connection[U]]

    def transmitter(self, *args: t.Any, **kwargs: t.Any) -> AbstractAsyncContextManager['Transmitter[U]', bool]:
        """ This method returns a context manager that creates and manages
        an instance of the `Transmitter` class. Packets are sent when they
        exit the context.

        Args:
            args: Arguments reserved for use in implementation.
            kwargs: Keyword arguments reserved for use in implementation.
        """

        @asynccontextmanager
        async def enter_transmitter_context():
            connection = self._connection_factory(*args, **kwargs)
            try:
                self._connections.append(connection)
                await connection._open_connection()
                transmitter = Transmitter[U](connection)
                yield transmitter
                await transmitter.send_instructions(*args, **kwargs)
            finally:
                self._connections.remove(connection)
                await connection._close_connection()

        return enter_transmitter_context()

    def receiver(self, after_sync_round: int, *args: t.Any, **kwargs: t.Any) \
            -> AbstractAsyncContextManager[AsyncIterator[tuple[int, Package[U]]], bool]:
        """ This method returns a context manager that creates an asynchronous
        iterator that yields instructions from the supporting platform.
        The context manager also manages the connection created for the iterator.

        Args:
            after_sync_round: The sync round number after which to receive instructions.
            args: Arguments reserved for use in implementation.
            kwargs: Keyword arguments reserved for use in implementation.

        Returns:
            An asynchronous iterator that returns a tuple consisting of the
            sync cycle number and a package of serialized instructions.

        Raises:
            ConnectionError: If error occurred while receiving packages.
        """

        async def _receiver(connection: Connection[U]):
            async for sync_round, package in connection.recv_instructions(after_sync_round, *args, **kwargs):
                yield sync_round, package

        @asynccontextmanager
        async def enter_receiver_context():
            connection = self._connection_factory(*args, **kwargs)
            try:
                self._connections.append(connection)
                await connection._open_connection()
                yield _receiver(connection)
            finally:
                self._connections.remove(connection)
                await connection._close_connection()

        return enter_receiver_context()

    @abstractmethod
    def _connection_factory(self, *args: t.Any, **kwargs: t.Any) -> Connection[U]:
        """ This method must return an instance of the Connection class.

        Args:
            args: Arguments reserved for use in implementation.
            kwargs: Keyword arguments reserved for use in implementation.
        """
