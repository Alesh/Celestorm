import typing as t
from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from typing import AsyncIterator

from celestia.node_api import Client, NodeAPI
from celestia.types import Namespace, Blob, Commitment

import celestorm.transport
from celestorm.encoding import Package, Instruction
from celestorm.transport import ConnectionClosed, Transmitter


class Connection[U](celestorm.transport.Connection[U]):
    """ This is a generic class that fully implements the
    `celestorm.transport.Connection` protocol for transmitting and receiving
    packets from the Celestia DA network.
    """

    def __init__(self, client: Client):
        self._client = client
        self.__api = NodeAPI | None

    @property
    def api(self) -> NodeAPI:
        if self.__api is not None:
            return t.cast(NodeAPI, self.__api)
        raise ConnectionClosed("Connection closed")

    def close(self):
        self.__api = None

    async def open_connection(self, *args: t.Any, auth_token: str = None,
                              response_timeout: float = 180, **kwargs: t.Any) -> None:
        self._cm = self._client.connect(auth_token, response_timeout=response_timeout)
        self.__api = await self._cm.__aenter__()

    async def close_connection(self) -> None:
        self.__api = None
        await self._cm.__aexit__(None, None, None)

    async def send_package(self, package: Package[U], namespace: Namespace = None, *args, **kwargs: t.Any) -> int:
        assert namespace is not None, "Parameter namespace missed"
        rv = await self.api.blob.submit(Blob(namespace, package))
        blob = await self.api.blob.get(rv.height, namespace, rv.commitments[0])
        return (rv.height << 16) + blob.index

    async def recv_packages(self, from_round: int, namespace: Namespace = None, *namespaces: Namespace, **kwargs: t.Any) \
            -> AsyncIterator[tuple[int, bytes, tuple[t.Any, ...]]]:
        assert namespace is not None, "Parameter namespace missed"
        namespaces = (namespace, *namespaces)
        get_height = lambda data: int(data['header']['height'])
        from_height = from_round >> 16
        async for curr_height in self.api.header.subscribe(deserializer=get_height):
            while from_height <= curr_height:
                for N in range(curr_height - from_height + 1):
                    height = from_height + N
                    if height > 0:
                        if blobs := await self.api.blob.get_all(height, *namespaces):
                            for blob in blobs:
                                yield (height << 16) + blob.index, blob.data, \
                                    (blob.namespace, blob.commitment, blob.share_version)
                from_height = curr_height + 1


class Transport[U](celestorm.transport.Transport[U], ABC):
    """ A generic abstract base class with partial implementation that defines
    the transport layer for receiving and sending instruction packages over
    the Celestia DA network.

    Args:
        url: The URL of the Celestia DA network, `ws://localhost:26658` by default.
        auth_token: The authorization token of the Celestia DA network.
        host: Changes the host in the default URL if it is set.
        port: Changes the port in the default URL if it is set.
    """

    def __init__(self, url: str = None, /, auth_token: str = None,
                 host: str = 'localhost', port: int = 26658):
        self._client = Client(url, auth_token=auth_token, host=host, port=port)
        super().__init__()

    def transmitter(self, namespace: Namespace, /, auth_token: str = None, response_timeout: float = 180) \
            -> AbstractAsyncContextManager['Transmitter[U]', bool]:
        """ Returns a context manager that helps send instructions to
        the Celestia DA network. See meth::``celestorm.transport.Transport.transmitter``
        for details.

        Args:
            namespace: The Celestia DA network namespace to which instructions are sent.
            response_timeout: The response timeout in seconds.
        """
        return super().transmitter(namespace, auth_token=auth_token, response_timeout=response_timeout)

    def receiver(self, from_round: int, *namespaces: Namespace, auth_token: str = None, **kwargs: t.Any) \
            -> AbstractAsyncContextManager[AsyncIterator[tuple[int, Package[U]]], bool]:
        """ Returns a context manager that returns an asynchronous iterator and
        helps receive instructions from the Celestia DA network.
        See meth::``celestorm.transport.Transport.transmitter`` for more details.

        Args:
            from_round: The sync round number from which instruction retrieval begins.
            namespace: The namespace of the Celestia DA network from which to receive instructions.
            namespace: Additional namespaces for receiving instructions.
        """
        if len(namespaces):
            if all(isinstance(namespace, Namespace) for namespace in namespaces):
                return super().receiver(from_round, *namespaces, auth_token=auth_token, **kwargs)
            raise TypeError("Invalid namespace argument")
        raise ValueError("Parameter namespace missed")

    def _connection_factory(self, *args, **kwargs) -> Connection[U]:
        # Binding to a concrete connection class.
        return Connection[U](self._client)

    @abstractmethod
    def _packager_factory(self, namespace: Namespace,
                          commitment: Commitment = None, share_version: int = None, **kwargs: t.Any) \
            -> type[Package[U]] | t.Callable[[bytes | t.Sequence[Instruction[U]]], Package[U]]:
        """ Must return a class implementing the instruction package
        ``celestorm.encoding.Package`` or a function creating its instance.

        Args:
            namespace: The namespace of the BLOB that contains the instructions.
            commitment: The commitment of the BLOB that contains the instructions.
            share_version: The shared version of the BLOB that contains the instructions.
            kwargs: Reserved named arguments.
        """
