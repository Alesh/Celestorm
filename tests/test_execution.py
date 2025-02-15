import asyncio
import logging
from collections import deque

from celestorm.execution import ExecutionError, logger
from celestorm.execution import Layer
from tests.impl.dclscud import Storage, Transport


async def test_storage(caplog, cud_bundles_maker, cud_state_maker):
    state = dict()
    ref_state = cud_state_maker()
    bundles = cud_bundles_maker()
    caplog.set_level(logging.INFO)

    caplog.clear()
    storage = Storage(state)
    last_sync_round = (await storage.get_last_round())
    for instructions in bundles:
        sync_round = last_sync_round + 1
        await storage.begin_transaction(sync_round)
        try:
            for instruction in instructions:
                await Layer._check_instruction(instruction, storage, sync_round)
                await storage.finalize_instruction(instruction)
            await storage.commit_transaction()
            logging.info(f"Sync round# {sync_round}; successful finalized")
        except Exception as exc:
            await storage.rollback_transaction(exc)
            if isinstance(exc, ExecutionError):
                logger.warning(f"Sync round# {sync_round}; dropped by error: {exc}", exc_info=exc)
            else:
                raise exc
        last_sync_round = sync_round

    assert (
            sorted(state.items(), key=lambda item: (item[0][0].__name__, item[0][1]))
            == sorted(ref_state.items(), key=lambda item: (item[0][0].__name__, item[0][1]))
    )

    assert (caplog.messages == [
        'Sync round# 1; successful finalized',
        'Sync round# 2; successful finalized',
        'Sync round# 3; successful finalized',
        'Sync round# 4; successful finalized',
        'Sync round# 5; successful finalized',
        'Sync round# 6; dropped by error: Instruction was late',
        'Sync round# 7; successful finalized'
    ])


async def transmitting(transport, bundles):
    last_round = 0
    for instructions in bundles:
        async with transport.transmitter(last_round) as transmit:
            for instruction in instructions:
                transmit(instruction)
        if transmit.sync_round is not None:
            last_round = transmit.sync_round
        await asyncio.sleep(0.1)


async def test_layer_expanded(cud_bundles_maker, cud_state_maker):
    state = dict()
    storage = Storage(state)
    accum = deque(maxlen=64)
    transport = Transport(accum)
    ref_state = cud_state_maker()
    bundles = cud_bundles_maker()

    task = asyncio.create_task(transmitting(Transport(accum), bundles))
    task.add_done_callback(lambda _: asyncio.get_running_loop().call_later(0.21, lambda: transport.close()))

    layer = Layer(transport, storage)
    from_round = (await storage.get_last_round()) + 1
    async with layer.start_recv(from_round) as receiver:
        async for sync_round, package in receiver:
            async with layer.start_sync(sync_round) as execute:
                async for instruction in package.deserialize():
                    await execute(instruction)

    assert (
            sorted(state.items(), key=lambda item: (item[0][0].__name__, item[0][1]))
            == sorted(ref_state.items(), key=lambda item: (item[0][0].__name__, item[0][1]))
    )


async def test_layer_folded(cud_bundles_maker, cud_state_maker):
    state = dict()
    storage = Storage(state)
    accum = deque(maxlen=64)
    transport = Transport(accum)
    ref_state = cud_state_maker()
    bundles = cud_bundles_maker()

    task = asyncio.create_task(transmitting(Transport(accum), bundles))
    task.add_done_callback(lambda _: asyncio.get_running_loop().call_later(0.21, lambda: transport.close()))

    layer = Layer(transport, storage)
    async with layer.start():
        await layer

    assert (
            sorted(state.items(), key=lambda item: (item[0][0].__name__, item[0][1]))
            == sorted(ref_state.items(), key=lambda item: (item[0][0].__name__, item[0][1]))
    )
