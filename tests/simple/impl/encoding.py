import typing as t

from celestorm import encoding
from celestorm.samples.simldcls import Instruction, OID


class Package(encoding.Package[OID]):
    """ Package of serialized instructions """

    def _instruction_deserializer(self) -> t.Callable[[bytes], Instruction]:
        return Instruction._deserialize
