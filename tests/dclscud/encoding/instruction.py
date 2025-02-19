import json
import typing as t
from dataclasses import is_dataclass, astuple
from datetime import datetime

import celestorm.encoding
import celestorm.encoding.protocols
from celestorm.encoding.errors import DeserializeError
from celestorm.encoding.protocols import Entity

type OID = tuple[type, type[t.Any, ...]]


def default_encoder(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class Instruction(celestorm.encoding.protocols.Instruction[OID]):
    """ Sample instruction """

    _registered: t.ClassVar[dict[str, type]] = dict()

    def __init__(self, entity: Entity[OID], revision: int = 0, **data: t.Any):
        if not is_dataclass(entity):
            raise TypeError("Parameter `entity` must be a dataclass.")
        if not isinstance(entity, Entity):
            raise TypeError("Parameter `entity` must support protocol `Entity`")
        if not (isinstance(revision, int) and revision >= 0):
            raise ValueError(f"Parameter `revision` must be an integer and >= 0")
        self.__oid = entity.oid
        self.__revision = revision
        if revision:
            if data:
                self.__payload = data
            else:
                self.__payload = None
        else:
            self.__payload = entity

    @property
    def oid(self) -> OID:
        """ Object ID """
        return self.__oid

    @property
    def payload(self) -> Entity[OID] | dict[str, t.Any]:
        """ Instruction payload. """
        return self.__payload

    @property
    def revision(self) -> int:
        """ Revision number """
        return self.__revision

    @property
    def method(self) -> t.Literal['CREATE', 'UPDATE', 'DELETE']:
        """ Method of instruction being processed. """
        if self.revision:
            if self.payload is not None:
                method = 'UPDATE'
            else:
                method = 'DELETE'
        else:
            method = 'CREATE'
        return t.cast(t.Literal['CREATE', 'UPDATE', 'DELETE'], method)

    @classmethod
    def register_dataclass(cls, dcls: type):
        if not is_dataclass(dcls):
            raise TypeError("Parameter `dcls` must be a dataclass.")
        cls._registered[dcls.__qualname__] = dcls

    def serialize(self) -> bytes:
        """ Method must serialize instruction to bytestring.  """
        dcls, keys = self.oid
        keys = keys if self.revision else ()
        payload = astuple(self.payload) if is_dataclass(self.payload) else self.payload

        return json.dumps([
            (dcls.__qualname__, *keys), self.revision,
            *([payload] if payload else []),
        ], separators=(',', ':'), default=default_encoder).encode('utf-8')

    @classmethod
    def deserialize(cls, data: bytes) -> 'Instruction':
        """ Method must deserialize instruction from bytestring.  """

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
