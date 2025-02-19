import asyncio
import logging
import typing as t
from abc import ABC
from collections import deque
from contextlib import asynccontextmanager

import celestorm.transport
import celestorm.transport.protocols
from .encoding import Package


class Connection(celestorm.transport.Connection):
    """ Example of a connection that can be used in tests. """

    connected: bool = False
    last_error: Exception | None = None
    do_close_exc = ConnectionError("Connection closed")

    def __init__(self, accum: deque[type[int, Package]]):
        self._accum = accum

    def close(self):
        self.last_error = Connection.do_close_exc

    async def open_connection(self, *args: t.Any, **kwargs: t.Any):
        self.last_error = None

    async def close_connection(self):
        self.close()

    async def send_package(self, package: Package,
                           last_round: int = 0, *args: t.Any, **kwargs: t.Any):
        if self.last_error is not None:
            raise self.last_error
        sync_round = last_round + 1
        self._accum.append((sync_round, package))
        return sync_round

    async def recv_packages(self, from_round: int, *args: t.Any, **kwargs: t.Any):
        while self.last_error is None:
            if len(self._accum):
                sync_round, package = self._accum.popleft()
                if sync_round >= from_round:
                    yield sync_round, package, ()
            else:
                await asyncio.sleep(0.1)

        if self.last_error and self.last_error != Connection.do_close_exc:
            raise self.last_error


class Transport(celestorm.transport.Transport, ABC):
    """ Example of transport that can be used in tests. """

    def __init__(self, accum: deque[type[int, Package]] = None):
        self.accum = accum if accum is not None else []
        super().__init__()

    @asynccontextmanager
    async def transmitter(self, last_round: int = 0):
        async with super().transmitter(last_round) as transmitter:
            yield transmitter
        logging.info(f"Sync round# {transmitter.sync_round}; {transmitter.sent_count} instructions are sent")

    def _connection_factory(self, *args: t.Any, **kwargs: t.Any):
        return Connection(self.accum)

    def _packager_factory(self, *args: t.Any, **kwargs: t.Any):
        return Package
