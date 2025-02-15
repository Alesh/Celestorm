"""
The `celestorm.execution` module contains generic abstract classes and protocols
for executing state-changing instructions in a distributed system.
"""
import asyncio
import logging
import typing as t
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from celestorm.encoding import Package
from celestorm.encoding.protocols import Instruction
from celestorm.transport import Transport
from .errors import ExecutionError, FinalizationError, SynchronizationError
from .protocols import Storage, TransactedStorage

logger = logging.getLogger(__name__)


class Layer[U]:
    """ The execution layer for state-changing instructions in a distributed
    system.

    Args:
        transport: Transport interface.
        storage: Distributed state storage interface.
    """

    def __init__(self, transport: Transport[U], storage: TransactedStorage[U]):
        assert isinstance(storage, TransactedStorage)
        self._main_task: asyncio.Task | None = None
        self._transport = transport
        self._storage = storage

    def __await__(self):
        if self._main_task and not self._main_task.done():
            return self._main_task.__await__()

    def start(self, *args: t.Any, **kwargs: t.Any) -> AbstractAsyncContextManager['Layer[U]', bool]:
        """ Returns a context manager that starts the execution layer and stops
        it upon exiting the context. """

        async def main():
            try:
                from_round = (await self._storage.get_last_round()) + 1
                async with self.start_recv(from_round, *args, **kwargs) as receiver:
                    async for sync_round, package in receiver:
                        async with self.start_sync(sync_round, *args, **kwargs) as execute:
                            async for instruction in package.deserialize():
                                await execute(instruction)
            except asyncio.CancelledError:
                pass

        @asynccontextmanager
        async def start_context():
            self._main_task = asyncio.create_task(main())
            try:
                yield self
            finally:
                if not self._main_task.done():
                    self._main_task.cancel()
                self._main_task = None

        return start_context()

    def start_recv(self, from_round: int, *args: t.Any, **kwargs: t.Any) \
            -> AbstractAsyncContextManager[AsyncIterator[tuple[int, Package[U]]], bool]:
        """ Returns a context manager for receiving instructions. Upon entering
        the context, a connection is established, and an async iterator of
        instructions is returned.

        Args:
            from_round: The sync round number from which instruction retrieval begins.
            args: Reserved positional arguments.
            kwargs: Reserved named arguments.

        Returns:
            An async iterator yielding a tuple of the sync round and the
            corresponding instruction package.
        """
        return self._transport.receiver(from_round, *args, **kwargs)

    def start_sync(self, sync_round: int, *args: t.Any, **kwargs: t.Any) \
            -> AbstractAsyncContextManager[t.Callable[[Instruction[U]], t.Awaitable[None]], bool]:
        """ Returns a context manager that initiates a sync round and starts
        a transactional storage session. Within the context, instructions are
        processed. Upon successful execution of all instructions without errors,
        the transaction is committed when exiting the context.

        Args:
            sync_round: The sync round number.
            args: Reserved positional arguments.
            kwargs: Reserved named arguments.

        Raises:
            ExecutionCritical: If a critical error occurs during synchronization.
            FinalizationError: If an error is detected during instruction finalization.
        """

        async def execute(instruction: Instruction[U]):
            await self._execute_instruction(sync_round, instruction)

        @asynccontextmanager
        async def start_sync_context():
            await self._storage.begin_transaction(sync_round, *args, **kwargs)
            try:
                yield execute
                await self._storage.commit_transaction()
            except Exception as exc:
                await self._storage.rollback_transaction(exc)
                if isinstance(exc, ExecutionError):
                    logger.warning(f"Sync round# {sync_round}; dropped by error: {exc}", exc_info=exc)
                else:
                    raise exc

        return start_sync_context()

    @staticmethod
    async def _check_instruction(instruction: Instruction[U], storage: Storage, sync_round: int = 0):
        """ Checks the validity of an instruction before execution.

        Args:
            instruction: The instruction to validate.
            sync_round: The current sync round number.
            storage: Distributed state storage interface.

        Raises:
            ExecutionError: If an error occurs during instruction execution.
            ExecutionCritical: If a critical error is detected.
        """
        assert isinstance(storage, Storage)
        if 0 < sync_round <= instruction.revision:
            raise SynchronizationError("Synchronisation lost")
        revision = await storage.get_revision_for(instruction.oid)
        if revision < instruction.revision:
            raise SynchronizationError("Synchronisation lost")
        elif revision > instruction.revision:
            raise ExecutionError("Instruction was late")

    async def _execute_instruction(self, sync_round: int, instruction: Instruction[U]):
        """ Executes an instruction and updates the object’s state in the storage.

        Args:
            sync_round: The current sync round number.
            instruction: The instruction to execute.

        Raises:
            FinalizationError: If an error is detected during instruction finalization.
        """
        await self._check_instruction(instruction, self._storage, sync_round)
        try:
            await self._storage.finalize_instruction(instruction)
        except Exception as exc:
            raise FinalizationError(f"Finalization error; {exc}") from exc
