import pytest
from celestia.node_api import Client


@pytest.mark.asyncio
async def test_testnet(node_provider):
    node, auth_token = await node_provider('light-0')
    client = Client(port=node.port['26658/tcp'])
    async with client.connect(auth_token) as api:
        balance = await api.state.balance()
        assert balance.amount

    node, auth_token = await node_provider('light-1')
    client = Client(port=node.port['26658/tcp'])
    async with client.connect(auth_token) as api:
        balance = await api.state.balance()
        assert balance.amount
