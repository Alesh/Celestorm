from datetime import datetime

import pytest

from celestorm.samples.simldcls import Instruction
from tests.modcls import Account, Message
from tests.simple.impl.encoding import Package


@pytest.fixture(scope="session")
def small_bundles_maker():
    return lambda addr='0123456789ABCDEF': [[
        Instruction(Account(addr, 'Alesh')),
        Instruction(Message(addr, datetime.fromisoformat('2025-01-01 00:00:00'), 'HI!')),
    ], [
        Instruction(Message(addr, datetime.fromisoformat('2025-01-01 00:00:01'), 'HNY!')),
    ]]


@pytest.fixture(scope="session")
def small_packages_maker(small_bundles_maker):
    def packages_maker(addr='0123456789ABCDEF', signer=None):
        bundles = small_bundles_maker(addr)
        return [(N + 1, Package.build(bundles[N], signer)) for N in range(len(bundles))]

    return packages_maker


@pytest.fixture(scope="module")
def small_state_maker():
    def state_maker(addr='0123456789ABCDEF'):
        return {
            (Account, (addr,)): (1, (addr, 'Alesh')),
            (Message, (addr, '2025-01-01T00:00:00')): (1, (addr, datetime(2025, 1, 1, 0, 0), 'HI!')),
            (Message, (addr, '2025-01-01T00:00:01')): (2, (addr, datetime(2025, 1, 1, 0, 0, 1), 'HNY!'))
        }

    return state_maker
