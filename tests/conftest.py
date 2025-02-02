from datetime import datetime

import pytest

from tests.impl.dclscud import Instruction, Package
from tests.models import Account, Message


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


@pytest.fixture(scope="session")
def cud_bundles_maker():
    return lambda addrA='0123456789ABCDEF', addrB='FEDCBA987654321': [[
        Instruction(Account(addrA, 'Alice')),
        Instruction(Message(addrA, datetime.fromisoformat('2025-01-01 00:00:00'), 'HI!')),
    ], [
        Instruction(Account(addrB, 'Bob')),
        Instruction(Message(addrB, datetime.fromisoformat('2025-01-01 00:00:01'), "Who's here?")),
    ], [
        Instruction(Message(addrA, datetime.fromisoformat('2025-01-01 00:00:01'), 'HNY!')),
    ], [
        Instruction(Message(addrA, datetime.fromisoformat('2025-01-01 00:00:03'), 'Am I there?')),
        Instruction(Message(addrA, datetime.fromisoformat('2025-01-01 00:00:04'), 'Who are you?')),
    ], [
        Instruction(Message(addrB, datetime.fromisoformat('2025-01-01 00:00:01'), "Who's here?"),
                    revision=2, message='Hi Alice!'),
    ], [
        Instruction(Message(addrB, datetime.fromisoformat('2025-01-01 00:00:01'), "Who's here?"),
                    revision=2),
    ], [
        Instruction(Message(addrA, datetime.fromisoformat('2025-01-01 00:00:03'), 'Am I there?'),
                    revision=4),
        Instruction(Message(addrA, datetime.fromisoformat('2025-01-01 00:00:04'), 'Who are you?'),
                    revision=4, message='Hi Bob!'),
    ]]


@pytest.fixture(scope="session")
def cud_packages_maker(cud_bundles_maker):
    def packages_maker(addrA='0123456789ABCDEF', addrB='FEDCBA987654321', signerA=None, signerB=None):
        def select_signer(payload):
            if getattr(payload, 'address', getattr(payload, 'from_address')) == addrA:
                return signerA
            return signerB

        bundles = cud_bundles_maker(addrA, addrB)
        return [(N + 1, Package.build(bundles[N], select_signer(bundles[N][0].payload)))
                for N in range(len(bundles))]

    return packages_maker


@pytest.fixture(scope="module")
def cud_state_maker():
    def state_maker(addrA='0123456789ABCDEF', addrB='FEDCBA987654321'):
        return {
            (Account, (addrA,)): (1, (addrA, 'Alice')),
            (Account, (addrB,)): (2, (addrB, 'Bob')),
            (Message, (addrA, '2025-01-01T00:00:00')): (1, (addrA, datetime(2025, 1, 1, 0, 0), 'HI!')),
            (Message, (addrA, '2025-01-01T00:00:01')): (3, (addrA, datetime(2025, 1, 1, 0, 0, 1), 'HNY!')),
            (Message, (addrB, '2025-01-01T00:00:01')): (5, (addrB, datetime(2025, 1, 1, 0, 0, 1), 'Hi Alice!')),
            (Message, (addrA, '2025-01-01T00:00:04')): (7, (addrA, datetime(2025, 1, 1, 0, 0, 4), 'Hi Bob!'))
        }

    return state_maker
