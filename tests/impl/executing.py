import logging
import typing as t
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import astuple, asdict

import celestorm.executing
import celestorm.storage
from celestorm.errors import ExecutionError
from celestorm.samples.simldcls import OID, Instruction
from celestorm.transport import Transport


class Session(celestorm.storage.Session[OID]):

    def __init__(self, storage: dict[t.Any, t.Any], sync_round: int):
        super().__init__(sync_round)
        self._storage = storage
        self._temp = None

    async def get_last_round(self) -> int:
        return max(sync_round for _, (sync_round, _) in self._storage.items()) if self._storage else 0

    async def get_revision_for(self, oid: OID) -> int:
        return self._storage.get(oid, (0, None))[0]

    async def round_accepted(self, sync_round: int) -> bool:
        return bool(sync_round_
                    for _, (sync_round_, _) in self._storage.items()
                    if sync_round == sync_round_)

    async def _apply_instruction(self, instruction: Instruction):
        if self._temp is None:
            raise RuntimeError("Use transaction")
        if instruction.method == 'CREATE':
            self._temp[instruction.oid] = (self.sync_round, astuple(instruction.payload))
        elif instruction.method == 'UPDATE':
            dcls = instruction.oid[0]
            revision, args = self._temp[instruction.oid]
            assert revision == instruction.revision
            old_state = dcls(*args)
            new_state = dcls(**dict(asdict(old_state), **instruction.payload))
            self._temp[instruction.oid] = (self.sync_round, astuple(new_state))
        else:
            revision, args = self._temp[instruction.oid]
            assert revision == instruction.revision
            del self._temp[instruction.oid]

    async def _begin_transaction(self):
        self._temp = deepcopy(self._storage)

    async def _commit_transaction(self):
        deleted_keys = set(self._storage) - set(self._temp)
        for key in deleted_keys:
            self._storage.pop(key, None)
        self._storage.update(self._temp)
        self._temp = None

    async def _rollback_transaction(self, *exc_info):
        self._temp = None


class Finalizer(celestorm.storage.Finalizer[OID]):

    def __init__(self, storage: dict[t.Any, t.Any] = None):
        self.state = storage if storage is not None else dict()
        super().__init__()

    @asynccontextmanager
    async def execution_round(self, sync_round: int):
        try:
            async with super().execution_round(sync_round) as finalize:
                yield finalize
            logging.info(f"Sync round# {sync_round}; successful finalized")
        except Exception as exc:
            if not isinstance(exc, ExecutionError):
                raise exc
            logging.warning(f"Sync round# {sync_round}; dropped by error: {exc}", exc_info=exc)

    def _session_factory(self, sync_round: int, *args, **kwargs) -> Session:
        return Session(self.state, sync_round)


class Layer(celestorm.executing.Layer[OID]):

    def __init__(self, transport: Transport):
        self.state = dict()
        self._transport = transport
        super().__init__()

    def _transport_factory(self, *args: t.Any, **kwargs: t.Any) -> Transport:
        return self._transport

    def _session_factory(self, sync_round: int, *args: t.Any, **kwargs: t.Any) -> Session:
        return Session(self.state, sync_round)
