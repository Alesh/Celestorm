import json
import typing as t
from dataclasses import Field, astuple, is_dataclass
from datetime import datetime

from celestorm import encoding
from celestorm.encoding.errors import DeserializeError
from celestorm.encoding.protocols import Entity


def default_encoder(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class Dataclass(Entity):
    """ Protocol for dataclasses """
    __dataclass_fields__: t.ClassVar[dict[str, Field[t.Any]]]


class OID(tuple[type[Dataclass], type[t.Any, ...]]):
    """ Object ID """


class Instruction(encoding.Instruction[OID]):
    """ This is a class of instructions represented as instances of data classes.
    """
    _registered: t.ClassVar[dict[str, type[Dataclass]]] = dict()

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
    def register_dataclass(cls, dcls: type[Dataclass]):
        cls._registered[dcls.__qualname__] = dcls

    def _serialize(self) -> bytes:
        dcls, keys = self.oid
        keys = keys if self.revision else ()
        payload = astuple(self.payload) if is_dataclass(self.payload) else self.payload

        return json.dumps([
            (dcls.__qualname__, *keys), self.revision,
            *([payload] if payload else []),
        ], separators=(',', ':'), default=default_encoder).encode('utf-8')

    @classmethod
    def _deserialize(cls, data: bytes) -> 'Instruction':
        deserialize_error = DeserializeError("Cannot deserialize instruction")
        try:
            (dcls_name, *keys), revision, *args = json.loads(data.decode('utf8'))
            payload = (*args, None)[0]
            if dcls := cls._registered.get(dcls_name):
                if revision:
                    return cls._new_from((dcls, tuple(keys)), revision, payload)
                else:
                    return cls(dcls(*payload), revision)
        except Exception as exc:
            raise deserialize_error from exc
        raise deserialize_error
