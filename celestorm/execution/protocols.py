import typing as t

from celestorm.encoding.protocols import Instruction

__all__ = ('Storage', 'TransactedStorage')


@t.runtime_checkable
class Storage[U](t.Protocol):
    """ A protocol for interacting with the distributed system's object storage.
    """

    async def get_last_round(self) -> int:
        """ Returns the last completed sync round or 0 if the storage has not yet been synchronized.
        """

    async def get_revision_for(self, oid: U) -> int:
        """ Returns the revision number of the object with the specified identifier.

        Args:
            oid: The identifier of the object whose revision is requested.

        Returns:
            The object's revision number or 0 if the object is not found.
        """

    async def round_accepted(self, sync_round: int) -> bool:
        """ Returns `True` if the specified sync round has been accepted.

        Args:
            sync_round: The sync round number to check.
        """


@t.runtime_checkable
class TransactedStorage[U](Storage[U], t.Protocol):
    """ An extended storage protocol with transaction support.
    """

    async def begin_transaction(self, sync_round: int, *args: t.Any, **kwargs: t.Any):
        """ Starts a transaction to modify the state of objects in the storage.

        Args:
            sync_round: The current sync round number.
            args: Reserved positional arguments.
            kwargs: Reserved named arguments.
        """

    async def finalize_instruction(self, instruction: Instruction[U]):
        """ Finalizes an instruction in the storage.

        Args:
            instruction: The instruction to finalize.
        """

    async def commit_transaction(self):
        """ Commits the transaction. """

    async def rollback_transaction(self, exc: Exception):
        """ Rolls back the transaction due to an error.

        Args:
            exc: The exception causing the rollback.
        """