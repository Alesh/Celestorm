import typing as t
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import asdict, astuple

import celestorm.execution
from .encoding import OID, Instruction


class Storage(celestorm.execution.TransactedStorage, ABC):
    def __init__(self, raw_storage: dict[t.Any, t.Any]):
        self._storage = raw_storage
        self._sync_round = None
        self._temp = None

    async def get_last_round(self) -> int:
        return max(sync_round for _, (sync_round, _) in self._storage.items()) if self._storage else 0

    async def get_revision_for(self, oid: OID) -> int:
        return self._storage.get(oid, (0, None))[0]

    async def round_accepted(self, sync_round: int) -> bool:
        return bool(sync_round_ for _, (sync_round_, _) in self._storage.items() if sync_round == sync_round_)

    async def begin_transaction(self, sync_round: int, *args: t.Any, **kwargs: t.Any):
        self._sync_round = sync_round
        self._temp = deepcopy(self._storage)

    async def finalize_instruction(self, instruction: Instruction):
        if self._sync_round is None:
            raise RuntimeError("You need to call begin_transaction before finalizing")
        if instruction.method == 'CREATE':
            self._temp[instruction.oid] = (self._sync_round, astuple(instruction.payload))
        elif instruction.method == 'UPDATE':
            dcls = instruction.oid[0]
            revision, args = self._temp[instruction.oid]
            assert revision == instruction.revision
            old_state = dcls(*args)
            new_state = dcls(**dict(asdict(old_state), **instruction.payload))
            self._temp[instruction.oid] = (self._sync_round, astuple(new_state))
        else:
            revision, args = self._temp[instruction.oid]
            assert revision == instruction.revision
            del self._temp[instruction.oid]

    async def commit_transaction(self):
        deleted_keys = set(self._storage) - set(self._temp)
        for key in deleted_keys:
            self._storage.pop(key, None)
        self._storage.update(self._temp)
        self._sync_round = self._temp = None

    async def rollback_transaction(self, exc: Exception):
        self._sync_round = self._temp = None
