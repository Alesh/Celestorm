import typing as t
from collections.abc import AsyncIterator

from celestorm.encoding import Package
from celestorm.encoding.protocols import Instruction

__all__ = ('Transmitter', 'Connection')


@t.runtime_checkable
class Transmitter[U](t.Protocol):
    """ A protocol defining the interface for forming an instruction package and sending it over the network.

    This interface is ``callable`` and accepts an instruction as a parameter to include in the package.

    Attributes:
        sent_count: The number of sent packages, 0 until a package is sent.
        sync_round: The sync round number in which the package was accepted by the network, None until sent.
    """
    sent_count: int
    sync_round: int | None

    def __call__(self, instruction: Instruction[U]): ...


@t.runtime_checkable
class Connection[U](t.Protocol):
    """ A protocol defining the interface for interacting with the distributed system's network to send and receive instruction packages.
    """

    def close(self):
        """ Forcibly closes the current network connection. """

    async def open_connection(self, *args: t.Any, **kwargs: t.Any) -> None:
        """ Establishes a connection to the network.

        Args:
            args: Reserved positional arguments.
            kwargs: Reserved named arguments.
        """

    async def close_connection(self) -> None:
        """ Closes the network connection.
        """

    def send_package(self, package: Package[U],
                     *args: t.Any, **kwargs: t.Any) -> t.Coroutine[t.Any, t.Any, int]:
        """ Sends an instruction package over the network.

        Args:
            package: The instruction package to send.
            args: Reserved positional arguments.
            kwargs: Reserved named arguments.

        Returns:
            The sync round number in which the package should be executed.
        """

    def recv_packages(self, from_round: int,
                      *args: t.Any, **kwargs: t.Any) -> AsyncIterator[tuple[int, bytes, tuple[t.Any, ...]]]:
        """ Creates an async iterator for receiving instruction packages from the network.

        Args:
            from_round: The sync round number from which instruction retrieval begins.
            args: Reserved positional arguments.
            kwargs: Reserved named arguments.

        Returns:
            An async iterator yielding a tuple of the sync round, the corresponding instruction package,
            and a tuple of additional parameters reserved for implementation use.

        Raises:
            ConnectionClosed: If the network connection is closed.
        """
