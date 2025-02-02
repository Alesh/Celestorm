import logging

from celestorm.examples.impl.executing import Finalizer


async def test_storage_finalizer(caplog, small_bundles_maker, small_state_maker):
    ref_state = small_state_maker()
    bundles = small_bundles_maker()
    caplog.set_level(logging.INFO)

    caplog.clear()
    finalizer = Finalizer()
    for instructions in bundles:
        sync_round = (await finalizer.get_last_round()) + 1
        async with finalizer.execution_round(sync_round) as finalize:
            for instruction in instructions:
                await finalize(instruction)
    assert finalizer.state == ref_state

    assert caplog.messages == [
        "Sync round# 1; successful finalized",
        "Sync round# 2; successful finalized"
    ]


async def test_storage_finalizer_cud(caplog, cud_bundles_maker, cud_state_maker):
    ref_state = cud_state_maker()
    bundles = cud_bundles_maker()
    caplog.set_level(logging.INFO)

    caplog.clear()
    finalizer = Finalizer()
    last_sync_round = (await finalizer.get_last_round())
    for instructions in bundles:
        sync_round = last_sync_round + 1
        async with finalizer.execution_round(sync_round) as finalize:
            for instruction in instructions:
                await finalize(instruction)
        last_sync_round = sync_round
    assert (
            sorted(finalizer.state.items(), key=lambda item: (item[0][0].__name__, item[0][1]))
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
