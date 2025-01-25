import typing as t
from abc import ABC
from contextlib import asynccontextmanager, AbstractAsyncContextManager

from celestorm.encoding import Instruction
from celestorm.errors import ExecutionError, ExecutionCritical
from .session import Session
from .storage import Storage


class Finalizer[U](Storage[U], ABC):
    """ Storage (state) finalizer."""

    def __init__(self):
        self._sessions: list[Session] = []

    def execution_round(self, sync_round: int, *args: t.Any, **kwargs: t.Any) \
            -> AbstractAsyncContextManager[t.Callable[[Instruction[U]], t.Awaitable[None]], bool]:
        """ Starts an execution (synchronisation) round.
        This method returns a context manager that provides a method for
        executing instructions. It also manages the process of executing
        them within a synchronisation round (transaction). When exiting
        the context, if there were no errors, the final state is committed,
        or all changes of the round are rolled back.

        Args:
            sync_round: The round of state synchronisation.
            args: Arguments reserved for use in implementation.
            kwargs: Keyword arguments reserved for use in implementation.
        """

        @asynccontextmanager
        async def enter_execution_context():
            session_ = self._session_factory(sync_round, *args, **kwargs)

            async def finalize(instruction: Instruction[U]):
                instruction = await self._check_instruction(session_, instruction)
                await session_._apply_instruction(instruction)

            try:
                self._sessions.append(session_)
                await session_._begin_transaction(*args, **kwargs)
                yield finalize
                await session_._commit_transaction()
            except Exception as exc:
                await session_._rollback_transaction(exc)
                raise exc
            finally:
                self._sessions.remove(session_)

        return enter_execution_context()

    async def _check_instruction(self, session: Session[U], instruction: Instruction[U]) -> Instruction[U]:
        """ Checking instructions before they are finalized. Additional checks
        are implemented by overriding this method or directly in the execution
        context.

        Args:
            session: The session in which the instructions are executed.
            instruction: The instruction being executed.
        """
        if instruction.revision < session.sync_round:
            revision = await session.get_revision_for(instruction.oid)
            if revision == instruction.revision:
                return instruction
            elif revision < instruction.revision:
                raise ExecutionCritical("Synchronisation lost")
            else:
                raise ExecutionError("Instruction was late")
        raise ExecutionCritical("Synchronisation lost")
