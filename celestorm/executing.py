import logging
import typing as t
from abc import ABC, abstractmethod

from celestorm.errors import ExecutionError
from celestorm.storage import Finalizer
from celestorm.transport import Transport

logger = logging.getLogger(__name__)


class Layer[U](Finalizer[U], ABC):

    async def finalizer(self, last_sync_round: int = None, *args: t.Any, **kwargs: t.Any):
        """ Starts the process of executing and finalizing instruction packets
        coming from the supporting platform.

        Args:
            last_sync_round:
                The last previously finalized round. If this is the first launch, please set it to 0.
                If value is not set, it will be got with method `.last_sync_round`.
        """
        last_sync_round = (await self.get_last_round()) if last_sync_round is None else last_sync_round
        transport = self._transport_factory(*args, **kwargs)
        async with transport.receiver(last_sync_round, *args, **kwargs) as receiver:
            async for sync_round, package in receiver:
                try:
                    async with self.execution_round(sync_round) as finalize:
                        for instruction in package.deserialize():
                            await finalize(instruction)
                except Exception as exc:
                    if not isinstance(exc, ExecutionError):
                        raise exc
                    logging.warning(f"Sync round# {sync_round}; dropped by error: {exc}", exc_info=exc)

    @abstractmethod
    def _transport_factory(self, *args: t.Any, **kwargs: t.Any) -> Transport[U]:
        pass
