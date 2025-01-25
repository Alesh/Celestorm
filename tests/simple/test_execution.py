import asyncio
import logging
from collections import deque

from tests.simple.impl.executing import Finalizer, Layer
from tests.simple.impl.transport import Transport


async def transmitting(transport_factory, bundles):
    last_round = 0
    try:
        transport = transport_factory()
        for instructions in bundles:
            async with transport.transmitter(last_round) as transmit:
                for instruction in instructions:
                    transmit(instruction)
            if transmit.sync_round is not None:
                last_round = transmit.sync_round
            await asyncio.sleep(0.1)
    except Exception as exc:
        logging.exception("Transmitting failed", exc_info=exc)


async def test_concept(caplog, cud_bundles_maker, cud_state_maker):
    tasks = set()
    accum = deque(maxlen=64)
    ref_state = cud_state_maker()
    bundles = cud_bundles_maker()
    caplog.set_level(logging.INFO)

    transmitting_task = asyncio.create_task(transmitting(lambda: Transport(accum), bundles))
    transmitting_task.add_done_callback(tasks.discard)
    tasks.add(transmitting_task)

    finalizer = Finalizer()
    transport = Transport(accum)
    last_sync_round = await finalizer.get_last_round()
    asyncio.get_running_loop().call_later(1.0, lambda: transport.close())

    async with transport.receiver(last_sync_round) as receiver:
        async for sync_round, package in receiver:
            async with finalizer.execution_round(sync_round) as finalize:
                for instruction in package.deserialize():
                    await finalize(instruction)

    assert (
            sorted(finalizer.state.items(), key=lambda item: (item[0][0].__name__, item[0][1]))
            == sorted(ref_state.items(), key=lambda item: (item[0][0].__name__, item[0][1]))
    )

    await asyncio.gather(*tasks)


async def test_layer(cud_bundles_maker, cud_state_maker):
    tasks = set()
    accum = deque(maxlen=64)
    ref_state = cud_state_maker()
    bundles = cud_bundles_maker()

    transmitting_task = asyncio.create_task(transmitting(lambda: Transport(accum), bundles))
    transmitting_task.add_done_callback(tasks.discard)
    tasks.add(transmitting_task)

    asyncio.get_running_loop().call_later(1.0, lambda: transport.close())
    transport = Transport(accum)
    layer = Layer(transport)
    await layer.finalizer()

    assert (
            sorted(layer.state.items(), key=lambda item: (item[0][0].__name__, item[0][1]))
            == sorted(ref_state.items(), key=lambda item: (item[0][0].__name__, item[0][1]))
    )

    await asyncio.gather(*tasks)
