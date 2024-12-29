from dataclasses import dataclass
from datetime import datetime

from celestorm.samples.simldcls import Instruction


@dataclass
class Account:
    """ User's account """
    address: str
    display_name: str

    @property
    def oid(self):
        return Account, (self.address,)


@dataclass(init=False)
class Message:
    """ User's messages """
    from_address: str
    wrote_at: datetime
    message: str

    def __init__(self, from_address: str, wrote_at: datetime | str, message: str):
        self.from_address = from_address
        self.wrote_at = wrote_at if isinstance(wrote_at, datetime) else datetime.fromisoformat(wrote_at)
        self.message = message

    @property
    def oid(self):
        return Message, (self.from_address, datetime.isoformat(self.wrote_at))


Instruction.register_dataclass(Account)
Instruction.register_dataclass(Message)
