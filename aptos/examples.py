import asyncio

from web3db.models import Profile

from utils import get_config_section, logger, read_json, Z8
from client import AptosClient

aptos_config = get_config_section('aptos')
amount_percentage = float(aptos_config['amount_percentage'])
price = float(aptos_config['price'])
collection_id = aptos_config['collection_id']


async def bluemove_batch_sell(profile: Profile):
    client = AptosClient(profile)
    balance = await client.get_v2_storage_ids_by_collection_id(collection_id)
    logger.info(f"{client.account_.address()} | Balance of aptmap - {balance}", id=profile.id)
    for data in balance[:int(len(balance) * amount_percentage / 100)]:
        payload = read_json('payload.json')
        token_name = data['current_token_data']['token_name']
        logger.info(f'Selling {token_name}', id=profile.id)
        storage_id = data['storage_id']
        payload['arguments'][0] = [{'inner': storage_id}]
        payload['arguments'][2] = [f'{int(price * Z8)}']
        await client.send_transaction(payload)


async def batch_balance(profiles: list[Profile]) -> int:
    tasks = []
    for profile in profiles:
        client = AptosClient(profile)
        tasks.append(asyncio.create_task(client.balance()))
    results = await asyncio.gather(*tasks)
    return sum(results)


async def check_v1_token_ownership(profile: Profile):
    client = AptosClient(profile)
    data = await client.v1_token_data(collection_id)
    if not data['data']['current_token_ownerships']:
        logger.error(f'{profile.id} | {client.account_.address()} {data["data"]["current_token_ownerships"]}')
    else:
        logger.success(f'{profile.id} | {client.account_.address()} {data["data"]["current_token_ownerships"]}')
