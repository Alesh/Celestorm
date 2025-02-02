import typing as t


@t.runtime_checkable
class Entity[U](t.Protocol):
    """ A protocol defining an object in the distributed system.
    """

    @property
    def oid(self) -> U:
        """ A unique identifier assigned to each object in the distributed system.
        """


@t.runtime_checkable
class Instruction[U](t.Protocol):
    """ A protocol defining an instruction for modifying the state of a distributed system object.
    """

    @property
    def oid(self) -> U:
        """ The identifier of the target object in the distributed system. """

    @property
    def payload(self) -> Entity[U] | dict[str, t.Any]:
        """ The instruction's payload, with its type depending on the instruction's purpose.
        """

    @property
    def revision(self) -> int:
        """ The expected revision number of the target object. """

    def serialize(self) -> bytes:
        """ Serializes the instruction into a byte string. """

    @classmethod
    def deserialize(cls, data: bytes) -> 'Instruction[U]':
        """ Deserializes an instruction from a byte string. """
