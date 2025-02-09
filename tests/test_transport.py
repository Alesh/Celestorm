import asyncio
import logging
from collections import deque

import pytest

from tests.impl.dclscud import Package, Transport



async def test_transmitter(caplog, small_bundles_maker):
    result = []
    accum = deque(maxlen=64)
    transport = Transport(accum)
    caplog.set_level(logging.INFO)
    bundles = small_bundles_maker()

    last_round = 0
    for instructions in bundles:
        async with transport.transmitter(last_round) as transmit:
            for instruction in instructions:
                transmit(instruction)
        if transmit.sync_round is not None:
            result.append(transmit.sync_round)
            last_round = transmit.sync_round

    assert result == [1, 2]
    assert caplog.messages == [
        "Sync round# 1; 2 instructions are sent",
        "Sync round# 2; 1 instructions are sent"
    ]
    assert tuple(accum) == tuple((N + 1, Package(bundles[N])) for N in range(len(bundles)))


async def test_transmitter_connection_close_error(small_bundles_maker):
    result = []
    transport = Transport()
    bundles = small_bundles_maker()

    asyncio.get_running_loop().call_later(0.21, lambda: transport.close())
    with pytest.raises(ConnectionError, match="Connection closed"):
        last_round = 0
        for instructions in bundles:
            async with transport.transmitter(last_round=last_round) as transmit:
                for instruction in instructions:
                    await asyncio.sleep(0.1)
                    transmit(instruction)
            if transmit.sync_round is not None:
                result.append(transmit.sync_round)
                last_round = transmit.sync_round
    assert result == [1]


async def test_receiver(small_bundles_maker):
    tasks = set()
    bundles = small_bundles_maker()
    ref_packages = [(N + 1, Package(bundles[N])) for N in range(len(bundles))]

    async def transmitting(transport):
        last_round = 0
        for instructions in bundles:
            async with transport.transmitter(last_round) as transmit:
                for instruction in instructions:
                    transmit(instruction)
            if transmit.sync_round is not None:
                last_round = transmit.sync_round
            await asyncio.sleep(0.1)

    for timeout, ref in [
        (0.21, [1, 2]),
        (0.11, [1]),
        (0.01, [])
    ]:
        result = dict()
        accum = deque(maxlen=64)
        transport = Transport(accum)

        tasks.add(asyncio.create_task(transmitting(Transport(accum))))

        last_sync_round = 0
        asyncio.get_running_loop().call_later(timeout, lambda: transport.close())
        async with transport.receiver(last_sync_round, accum) as receiver:
            async for sync_round, package in receiver:
                async for instruction in package.deserialize():
                    result.setdefault(sync_round, []).append(instruction)

        assert list(result.keys()) == ref
        assert (tuple(Package(instructions) for instructions in result.values())
                == tuple(package for _, package in ref_packages[:len(ref)]))

    await asyncio.gather(*tasks)
