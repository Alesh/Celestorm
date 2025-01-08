import asyncio
import logging
import typing as t
from collections import deque
from contextlib import asynccontextmanager
from typing import AsyncIterator

import celestorm.transport
from .encoding import Package


class Connection(celestorm.transport.Connection):
    last_error: Exception = None
    do_close_exc = ConnectionError("Connection closed")

    def close(self):
        self.last_error = Connection.do_close_exc

    def _packager_factory(self, *args: t.Any, **kwargs: t.Any) -> type[Package]:
        return Package

    async def _send_package(self, package: Package, accum: deque[type[int, Package]] = None,
                            last_round: int = 0, *args: t.Any, **kwargs: t.Any) -> int:
        accum = accum if accum is not None else []
        if self.last_error is not None:
            raise self.last_error
        sync_round = last_round + 1
        accum.append((sync_round, package))
        return sync_round

    async def _recv_packages(self, after_sync_round: int, accum: deque[type[int, Package]] = None,
                             *args: t.Any, **kwargs: t.Any) -> AsyncIterator[tuple[int, bytes, tuple[t.Any, ...]]]:
        if accum is None:
            raise AttributeError("Parameter 'accum' is not set")
        while self.last_error is None:
            if len(accum):
                sync_round, package = accum.popleft()
                if sync_round > after_sync_round:
                    yield sync_round, package, ()
            else:
                await asyncio.sleep(0.1)

        if self.last_error and self.last_error != Connection.do_close_exc:
            raise self.last_error


class Transport(celestorm.transport.Transport):

    @asynccontextmanager
    async def transmitter(self, accum: deque[type[int, Package]] = None, last_round: int = 0):
        async with super().transmitter(accum, last_round) as transmitter:
            yield transmitter
        logging.info(f"Sync round# {transmitter.sync_round}; {transmitter.sent_count} instructions are sent")

    def _connection_factory(self, *args, **kwargs) -> Connection:
        return Connection()
