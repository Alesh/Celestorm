import json
import typing as t
from dataclasses import is_dataclass, astuple, asdict
from datetime import datetime

import tests.impl.encoding
import tests.impl.execution
import tests.impl.transport
from celestorm.encoding.errors import DeserializeError
from celestorm.encoding.protocols import Entity
from tests.impl.encoding import OID


def default_encoder(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class Instruction(tests.impl.encoding.Instruction):
    """ Example of an instruction adapted to use dataclass as a payload. """

    _registered: t.ClassVar[dict[str, type]] = dict()

    def __init__(self, entity: Entity[OID], revision: int = 0, **data: t.Any):
        if not is_dataclass(entity):
            raise TypeError("Parameter `entity` must be a dataclass.")
        super().__init__(entity, revision, **data)

    @classmethod
    def register_dataclass(cls, dcls: type):
        if not is_dataclass(dcls):
            raise TypeError("Parameter `dcls` must be a dataclass.")
        cls._registered[dcls.__qualname__] = dcls

    def serialize(self):
        dcls, keys = self.oid
        keys = keys if self.revision else ()
        payload = astuple(self.payload) if is_dataclass(self.payload) else self.payload

        return json.dumps([
            (dcls.__qualname__, *keys), self.revision,
            *([payload] if payload else []),
        ], separators=(',', ':'), default=default_encoder).encode('utf-8')

    @classmethod
    def deserialize(cls, data: bytes):

        def create(oid: OID, revision: int, payload: dict[str, t.Any]):
            inst = cls.__new__(cls)
            inst._Instruction__oid = oid
            inst._Instruction__revision = revision
            inst._Instruction__payload = payload
            return inst

        deserialize_error = DeserializeError("Cannot deserialize instruction")
        try:
            (dcls_name, *keys), revision, *args = json.loads(data.decode('utf8'))
            payload = (*args, None)[0]
            if dcls := cls._registered.get(dcls_name):
                if revision:
                    return create((dcls, tuple(keys)), revision, payload)
                else:
                    return cls(dcls(*payload), revision)
        except Exception as exc:
            raise deserialize_error from exc
        raise deserialize_error


class Package(tests.impl.encoding.Package):
    """ Example of a package adapted to use dataclass as a payload of instructions. """

    def _deserialize_instruction(self, instruction: bytes):
        return Instruction.deserialize(instruction)


class Transport(tests.impl.transport.Transport):
    """ Example of transport that uses packages adapted to use dataclass. """

    def _packager_factory(self, *args: t.Any, **kwargs: t.Any):
        return Package


class Storage(tests.impl.execution.Storage):

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
