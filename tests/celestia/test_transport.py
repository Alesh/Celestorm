import asyncio
import logging
import typing as t
from contextlib import asynccontextmanager

import pytest
from celestia.node_api import Client
from celestia.types import Namespace, Commitment

import celestorm.celestia.transport
from tests.dclscud.encoding import Package, Instruction, OID


class Transport(celestorm.celestia.transport.Transport[OID]):

    @asynccontextmanager
    async def transmitter(self, namespace, /, auth_token=None, response_timeout: float = 180):
        async with super().transmitter(namespace, auth_token, response_timeout) as transmitter:
            yield transmitter
        logging.info(f"Sync round# {transmitter.sync_round}; "
                     f"{transmitter.sent_count} instructions are sent; namespace: {namespace}")

    def _packager_factory(self, namespace: Namespace,
                          commitment: Commitment = None, share_version: int = None, **kwargs: t.Any) -> \
            type[Package] | t.Callable[[bytes | t.Sequence[Instruction]], Package]:
        # Binding to a concrete instruction package class.
        return Package


async def test_transmitter(node_provider, caplog, small_bundles_maker):
    result = []
    namespace = Namespace(b'Alesh!test')
    node, auth_token = await node_provider('light-0')
    transport = Transport(port=node.port['26658/tcp'])
    caplog.set_level(logging.INFO)
    bundles = small_bundles_maker()

    for instructions in bundles:
        async with transport.transmitter(namespace, auth_token) as transmit:
            for instruction in instructions:
                transmit(instruction)
        if transmit.sync_round is not None:
            result.append(transmit.sync_round)

    assert len(result) == 2
    assert caplog.messages == [
        f"Sync round# {result[N]}; {len(bundles[N])} instructions are sent; namespace: {namespace}" for N in
        range(len(result))
    ]

    result = []
    caplog.clear()
    with pytest.raises(ConnectionError):
        N = 0
        for instructions in bundles:
            async with transport.transmitter(namespace, auth_token) as transmit:
                if N == 1:
                    transport.close()
                for instruction in instructions:
                    transmit(instruction)
            N += 1
            if transmit.sync_round is not None:
                result.append(transmit.sync_round)

    assert len(result) == 1
    assert caplog.messages == [
        f"Sync round# {result[N]}; {len(bundles[N])} instructions are sent; namespace: {namespace}" for N in
        range(len(result))
    ]


async def test_receiver(node_provider, small_bundles_maker):
    async def do_transmitting(transport, namespace, auth_token, bundles):
        result = []
        for instructions in bundles:
            async with transport.transmitter(namespace, auth_token) as transmit:
                for instruction in instructions:
                    transmit(instruction)
            if transmit.sync_round is not None:
                result.append(transmit.sync_round)
        return result

    async def do_receiving(transport, namespace, auth_token, last_height, expected, emit_close=None):
        result = dict()
        from_round = (last_height + 1) << 16
        async with transport.receiver(from_round, namespace, auth_token=auth_token) as receiver:
            async for sync_round, package in receiver:
                async for instruction in package.deserialize():
                    result.setdefault(sync_round, []).append(instruction)
                expected -= 1
                if not expected:
                    break
                elif emit_close is not None and expected == emit_close:
                    transport.close()
        return result

    namespace = Namespace(b'Alesh!test')
    node, auth_token = await node_provider('light-0')
    transport = Transport(port=node.port['26658/tcp'])
    node_a, auth_token_a = await node_provider('light-1')
    transport_a = Transport(port=node_a.port['26658/tcp'])
    bundles = small_bundles_maker()

    get_height = lambda data: int(data['header']['height'])
    client = Client(port=node.port['26658/tcp'])

    async with client.connect(auth_token) as api:
        last_height = await api.header.local_head(deserializer=get_height)
    transmitting_task = asyncio.create_task(do_transmitting(transport_a, namespace, auth_token_a, bundles))
    receiving_task = asyncio.create_task(do_receiving(transport, namespace, auth_token, last_height, len(bundles)))

    async with asyncio.timeout(60):
        await asyncio.gather(transmitting_task, receiving_task)

    t_result = transmitting_task.result()
    r_result = receiving_task.result()

    assert len(r_result) == len(bundles)
    assert list(r_result.keys()) == t_result
    assert (list(Package(instructions) for instructions in r_result.values())
            == list(Package(instructions) for instructions in bundles))

    # close handling
    async with client.connect(auth_token) as api:
        last_height = await api.header.local_head(deserializer=get_height)
    transmitting_task = asyncio.create_task(do_transmitting(transport_a, namespace, auth_token_a, bundles))
    receiving_task = asyncio.create_task(do_receiving(transport, namespace, auth_token, last_height, len(bundles), 1))

    async with asyncio.timeout(60):
        await asyncio.gather(transmitting_task, receiving_task)

    t_result = transmitting_task.result()
    r_result = receiving_task.result()

    assert len(r_result) == 1
    assert list(r_result.keys()) == t_result[:1]
