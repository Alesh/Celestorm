import typing as t
from abc import ABC, abstractmethod

from .session import Session


class Storage[U](ABC):
    """ Storage abstract base class. """

    async def get_last_round(self) -> int:
        """ Returns the last completed round of synchronization, or 0 if
        synchronization has never occurred.
        """
        return await self._session_factory(0).get_last_round()

    async def get_revision_for(self, oid: U) -> int:
        """ Retrieves the revision number for the specified object.

        The revision number corresponds to the synchronization round in which
        the object's state was last changed.

        Args:
            oid: The object identifier for which to retrieve the revision.

        Returns:
            The object's revision number, or 0 if not found.
        """
        return await self._session_factory(0).get_revision_for(oid)

    async def round_accepted(self, sync_round: int) -> bool:
        """ Returns whether the given synchronization round has been accepted.
        Args:
            sync_round: The synchronization round number.
        """
        return await self._session_factory(0).round_accepted(sync_round)

    @abstractmethod
    def _session_factory(self, sync_round: int, *args: t.Any, **kwargs: t.Any) -> Session[U]:
        """ This method must return an instance of the `celestorm.storage.Session`
        class.

        Args:
            sync_round: Round number for synchronization.
            args: Arguments reserved for use in implementation.
            kwargs: Keyword arguments reserved for use in implementation.
        """
