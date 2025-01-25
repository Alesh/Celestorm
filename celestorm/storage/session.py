import typing as t
from abc import ABC, abstractmethod

from celestorm.encoding import Instruction


class Session[U](ABC):
    """ Abstract base class for managing instruction execution sessions.
    """

    def __init__(self, sync_round: int, *args, **kwargs) -> None:
        self.__sync_round = sync_round

    @property
    def sync_round(self) -> int:
        """ Session sync round."""
        return self.__sync_round

    @abstractmethod
    async def get_last_round(self) -> int:
        """ Returns the last completed round of synchronization, or 0 if
        synchronization has never occurred.
        """

    @abstractmethod
    async def get_revision_for(self, oid: U) -> int:
        """ Retrieves the revision number for the specified object.

        The revision number corresponds to the synchronization round in which
        the object's state was last changed.

        Args:
            oid: The object identifier for which to retrieve the revision.

        Returns:
            The object's revision number, or 0 if not found.
        """

    @abstractmethod
    async def round_accepted(self, sync_round: int) -> bool:
        """ Returns whether the given synchronization round has been accepted.
        Args:
            sync_round: The synchronization round number.
        """

    @abstractmethod
    async def _apply_instruction(self, instruction: Instruction[U]):
        """ Applies a state change instruction within the current session's
        transaction. """

    @abstractmethod
    async def _begin_transaction(self, *args: t.Any, **kwargs: t.Any):
        """ Starts a new transaction for the current sync round. """

    @abstractmethod
    async def _commit_transaction(self):
        """ Commits the  current transaction. """

    @abstractmethod
    async def _rollback_transaction(self, exc: Exception):
        """ Rolls back the current transaction. """
