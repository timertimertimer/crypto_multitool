import asyncio

from web3db import DBHelper

from client import *
from evm.config import *
from models import *
from utils import *

from dotenv import load_dotenv


load_dotenv()

db = DBHelper(os.getenv('CONNECTION_STRING'))


async def check_balance_batch(network: Network):
    profiles = await db.get_all_from_table(Profile)
    tasks = []
    for profile in profiles:
        client = Client(network, profile)
        tasks.append(asyncio.create_task(client.get_native_balance(echo=True)))
    total = await asyncio.gather(*tasks)
    ans = 0
    for el in total:
        ans += el.Ether
    logger.info(f'Total: {ans}')


async def check_xp_linea():
    lxp_contract_address = '0xd83af4fbD77f3AB65C3B1Dc4B38D7e67AEcf599A'
    profiles = await db.get_all_from_table(Profile)
    tasks = []
    for profile in profiles:
        client = Client(Linea, account=Account.from_key(decrypt(profile.evm_private, os.getenv('PASSPHRASE'))))
        client.default_abi = read_json(LXP_ABI_PATH)
        tasks.append(asyncio.create_task(client.balance_of(token_address=lxp_contract_address)))
    result = await asyncio.gather(*tasks)
    logger.success(f'Total - {sum([el.Ether for el in result])} LXP')


async def have_balance(client: Client, ethers: float = 0.002, echo: bool = False) -> bool:
    balance = await client.get_native_balance(echo=echo)
    if balance.Ether > ethers:
        return True
    return False


async def get_wallets_with_balance(network: Network):
    profiles = await db.get_all_from_table(Profile)
    tasks = []
    for profile in profiles:
        client = Client(network, account=Account.from_key(decrypt(profile.evm_private, os.getenv('PASSPHRASE'))))
        tasks.append(asyncio.create_task(have_balance(client)))
    await asyncio.gather(*tasks)


async def opbnb_bridge(profile: Profile, amount: float = 0.002):
    if await have_balance(Client(opBNB, profile)):
        return
    client = Client(BNB, profile)
    contract_address = '0xF05F0e4362859c3331Cb9395CBC201E3Fa6757Ea'
    client.default_abi = read_json(OPBNB_BRIDGE_ABI_PATH)
    contract = client.w3.eth.contract(
        address=client.w3.to_checksum_address(contract_address),
        abi=client.default_abi
    )
    tx_hash = await client.send_transaction(
        to=contract_address,
        data=contract.encodeABI('depositETH', args=[1, b'']),
        value=TokenAmount(amount).Wei
    )
    if tx_hash:
        return tx_hash
    return False


if __name__ == '__main__':
    asyncio.run(check_balance_batch(Ethereum))
