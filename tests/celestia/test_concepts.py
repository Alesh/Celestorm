import asyncio

import pytest
from celestia.node_api import Client
from celestia.types import Namespace, Blob

from tests.dclscud.encoding import Package


async def test_transport_concept(node_provider, small_bundles_maker):
    bundles = small_bundles_maker()
    namespace = Namespace(b'Alesh!test')
    node, auth_token = await node_provider('light-0')
    client = Client(port=node.port['26658/tcp'])
    get_height = lambda data: int(data['header']['height'])

    async def transmitting():
        result = []
        async with client.connect(auth_token) as api:
            for instructions in bundles:
                package = Package(instructions)
                rv = await api.blob.submit(Blob(namespace, package))
                result.append(rv.height)
        return result

    async def receiving(last_height, *, for_rounds=3, emit_error=False):
        result = dict()
        async with client.connect(auth_token) as api:
            async for curr_height in api.header.subscribe(deserializer=get_height):
                while last_height < curr_height:
                    for N in range(curr_height - last_height):
                        height = last_height + N + 1
                        if blobs := await api.blob.get_all(height, namespace=namespace):
                            for blob in blobs:
                                result.setdefault(height, []).append((blob.index, blob.commitment))
                    last_height = curr_height
                if from_height + for_rounds < curr_height:
                    if emit_error:
                        raise ConnectionResetError("Emitted error!")
                    else:
                        break
        return result

    async with client.connect(auth_token) as api:
        from_height = last_height = await api.header.local_head(deserializer=get_height)

    # transmitting
    t_result = await transmitting()
    assert len(t_result) == 2

    # receiving
    async with asyncio.timeout(30):
        r_result = await receiving(from_height)
    assert list(r_result.keys()) == t_result

    r_result_values = [
        [(1, b'\x02Bd\x1brvd\xb5\xd8\xfc\x89B\xbe\x10\xd0u\xca\x18x\x1e\xa7\xcc\x07C\xd2\xad\xc4]{\xbf^3')],
        [(1, b"\x04\xdc\xe6\x18\x01r!\x0e\x15DL\xf9\xc23V\x0b\xd5y'o\xd2\xb4\xe3\x8d\xd9\x1f\r\x94\x86\x88\xa3\x1b")]
    ]

    assert list(r_result.values()) == r_result_values

    with pytest.raises(ConnectionResetError, match="Emitted error!"):
        async with asyncio.timeout(30):
            r_result = await receiving(from_height, emit_error=True)

    assert t_result == list(r_result)
    assert list(r_result.values()) == r_result_values
