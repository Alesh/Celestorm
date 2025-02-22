import asyncio
import logging
from time import sleep

import pytest
from celestia.node_api import Client

from tests.celestia.utils import get_auth_token, start_testnet, stop_testnet
from tests.docker import Containers
from tests.conftest import small_bundles_maker  # noqa


@pytest.fixture(scope="session")
def containers():
    cnt = 10
    need_shutdown = False
    containers = Containers('cs_testnet')
    while cnt:
        if containers:
            break
        if not need_shutdown:
            start_testnet()
            need_shutdown = True
        cnt -= 1
        sleep(10 - cnt)
        containers = Containers('cs_testnet')
    else:
        RuntimeError("Cannot start testnet")
    yield containers
    if need_shutdown:
        stop_testnet()


@pytest.fixture(scope="session")
def ready_nodes():
    yield dict()


@pytest.fixture
def node_provider(containers, ready_nodes):
    #
    async def node_provider_(name):
        if name in ready_nodes:
            return ready_nodes[name]
        elif node := containers.get_by_name_first(name):
            auth_token = get_auth_token(node)
            cnt = 10
            while cnt:
                cnt -= 1
                try:
                    async with Client(port=node.port['26658/tcp']).connect(auth_token) as api:
                        balance = await api.state.balance()
                        if balance.amount:
                            ready_nodes[name] = node, auth_token
                            return ready_nodes[name]
                except Exception as exc:
                    if not cnt:
                        raise exc
                if cnt:
                    await asyncio.sleep(10 - cnt)
            else:
                raise RuntimeError(f"Node '{name}' not ready")
        else:
            raise RuntimeError(f"Node '{name}' not found")

    return lambda name: node_provider_(name)


@pytest.fixture
async def bridge0client(node_provider, ready_nodes):
    node, auth_token = await node_provider('bridge-0')
    return Client(auth_token, host='localhost', port=node.port['26658/tcp'])


@pytest.fixture
async def light0client(node_provider, ready_nodes):
    node, auth_token = await node_provider('light-0')
    return Client(auth_token=auth_token, host='localhost', port=node.port['26658/tcp'])


@pytest.fixture
async def light1client(node_provider, ready_nodes):
    node, auth_token = await node_provider('light-1')
    return Client(auth_token=auth_token, host='localhost', port=node.port['26658/tcp'])
