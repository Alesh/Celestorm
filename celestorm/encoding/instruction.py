"""
An instruction is one of the key features. It describes how exactly the state
of an object in a distributed system should change, under what conditions and
how exactly this happens.
"""
import typing as t
from abc import ABC, abstractmethod

from celestorm.encoding.protocols import Entity


class Instruction[U](ABC):
    """
    Abstract base class defining the interface for instructions processed
    by the execution layer.

    This class represents an instruction that describes how the state
    of an object in a distributed system should change.

    Args:
        entity: The entity associated with this instruction.
        revision: The revision number of the instruction. Defaults to 0.
        **data: Additional data for the instruction payload.

    Raises:
        TypeError: If `entity` does not support the `Entity` protocol.
        ValueError: If `revision` is not a non-negative integer.
    """

    def __init__(self, entity: Entity[U], revision: int = 0, **data: t.Any):
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
    def oid(self) -> U:
        """ Unique identifier for the object to which this instruction applies.

        See form more details :class:`~celestorm.abc.encoding.protocols.Entity`.
        """
        return self.__oid

    @property
    def payload(self) -> Entity[U] | dict[str, t.Any]:
        """ Instruction payload.

        This property returns either the associated entity or additional
        data as a dictionary, depending on the instruction's revision.
        """
        return self.__payload

    @property
    def revision(self) -> int:
        """ Revision number of the object to which this instruction applies. """
        return self.__revision

    @classmethod
    def _new_from(cls, oid: U, revision: int, payload: dict[str, t.Any]) -> 'Instruction[U]':
        """ Creates a new Instruction instance from the given internal parameters. """
        inst = cls.__new__(cls)
        inst.__oid = oid
        inst.__revision = revision
        inst.__payload = payload
        return inst

    @abstractmethod
    def _serialize(self) -> bytes:
        """ Serializes the instruction into a byte string. """

    @classmethod
    @abstractmethod
    def _deserialize(cls, data: bytes) -> 'Instruction[U]':
        """ Deserializes the instruction from a byte string. """
