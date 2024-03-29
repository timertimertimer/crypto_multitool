import asyncio
import csv
import random

from dotenv import load_dotenv

from curl_cffi.requests import AsyncSession, RequestsError
from eth_account import Account
from eth_account.messages import encode_typed_data, encode_defunct
from web3.exceptions import ContractLogicError
from web3db.utils import DEFAULT_UA

from evm.client import Client
from evm.config import ABIS_DIR
from evm.models import ZetaChain, BNB, TokenAmount

from utils import read_json, set_windows_event_loop_policy, logger, sleep

load_dotenv()
set_windows_event_loop_policy()

pool_abi = [
    {
        "type": "function",
        "name": "addLiquidityETH",
        "inputs": [
            {"name": "_token", "type": "address"},
            {"name": "_amountTokenDesired", "type": "uint256"},
            {"name": "_amountTokenMin", "type": "uint256"},
            {"name": "_amountETHMin", "type": "uint256"},
            {"name": "_to", "type": "address"},
            {"name": "_deadline", "type": "uint256"},
        ],
        "outputs": [],
        "stateMutability": "payable",
        "constant": False,
    }
]

encoding_contract_abi = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "bytes", "name": "path", "type": "bytes"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint128", "name": "amount", "type": "uint128"},
                    {
                        "internalType": "uint256",
                        "name": "minAcquired",
                        "type": "uint256",
                    },
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"},
                ],
                "internalType": "struct Swap.SwapAmountParams",
                "name": "params",
                "type": "tuple",
            }
        ],
        "name": "swapAmount",
        "outputs": [
            {"internalType": "uint256", "name": "cost", "type": "uint256"},
            {"internalType": "uint256", "name": "acquire", "type": "uint256"},
        ],
        "stateMutability": "payable",
        "type": "function",
    }
]

multicall_abi = [
    {
        "inputs": [{"internalType": "bytes[]", "name": "data", "type": "bytes[]"}],
        "name": "multicall",
        "outputs": [{"internalType": "bytes[]", "name": "results", "type": "bytes[]"}],
        "stateMutability": "payable",
        "type": "function",
    }
]
ultiverse_badge_abi = [
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "expireAt",
                "type": "uint256"
            },
            {
                "internalType": "uint256",
                "name": "tokenId",
                "type": "uint256"
            },
            {
                "internalType": "uint256",
                "name": "eventId",
                "type": "uint256"
            },
            {
                "internalType": "bytes",
                "name": "signature",
                "type": "bytes"
            }
        ],
        "name": "buy",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]
izumi_WZETA_stZETA_pool_abi = read_json(ABIS_DIR / 'zetachain/izumi_wzeta_stzeta_pool.json')
invitation_manager_abi = read_json(ABIS_DIR / 'zetachain/invitation_manager.json')
stZETA_minter = read_json(ABIS_DIR / 'zetachain/stZETA_minter.json')
wstZETA = read_json(ABIS_DIR / 'zetachain/wstZETA.json')

zeta_token_address = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'
stZETA_token_address = '0x45334a5B0a01cE6C260f2B570EC941C680EA62c0'
WZETA_token_address = '0x5F0b1a82749cb4E2278EC87F8BF6B618dC71a8bf'
stZETA_af_token_address = '0xcba2aeEc821b0B119857a9aB39E09b034249681A'
wstZETA_token_address = '0x7AC168c81F4F3820Fa3F22603ce5864D6aB3C547'
bnb_zeta_token_address = '0x48f80608b672dc30dc7e3dbbd0343c5f02c738eb'

izumi_WZETA_stZETA_pool_address = '0x08F4539f91faA96b34323c11C9B00123bA19eef3'
af_stZETA_deposit_address = '0xcf1A40eFf1A4d4c56DC4042A1aE93013d13C3217'
stZETAMinter_address = '0xcf1A40eFf1A4d4c56DC4042A1aE93013d13C3217'
eddy_swap_address = '0xDE3167958Ad6251E8D6fF1791648b322Fc6B51bD'

zrc20_tokens = [
    bnb_zeta_token_address,
    '0xd97B1de3619ed2c6BEb3860147E30cA8A7dC9891',  # ETH.ETH
    WZETA_token_address,
    stZETA_token_address,
    '0x13A0c5930C028511Dc02665E7285134B6d11A5f4',  # BTC.BTC
    '0x7c8dDa80bbBE1254a7aACf3219EBe1481c6E01d7',  # USDT(ETH)
    '0x91d4F0D54090Df2D81e834c3c8CE71C6c865e79F',  # USDT(BSC)
    '0x0cbe0dF132a6c6B4a2974Fa1b7Fb953CF0Cc798a',  # USDC(ETH)
    '0x05BA149A7bd6dC1F937fA9046A9e05C05f3b18b0'  # USDC(BSC)
]
delay_between_http_requests = 10
delay_between_rpc_requests = 10


async def zeta_and_bnb_price() -> tuple[float, float]:
    return await Client.get_token_price('ZETA'), await Client.get_token_price('BNB')


class ZetachainHub:

    def __init__(self, client: Client, proxy: str):
        self.client = client
        self.proxy = proxy
        headers = {
            "User-Agent": DEFAULT_UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Sec-Ch-Ua": '"Chromium";v="120", "Not(A:Brand";v="24", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Connection": "keep-alive",
        }
        self.session = AsyncSession(proxies={"http": proxy}, headers=headers)
        self.tasks = {
            "SEND_ZETA": self.receive_and_transfer,
            "RECEIVE_ZETA": self.receive_and_transfer,
            "POOL_DEPOSIT_ANY_POOL": self.lp_pool,
            "ONE_INVITE_ACCEPTED": None,
            "TEN_INVITES_ACCEPTED": None,
            "FIFTY_INVITES_ACCEPTED": None,
            "WALLET_VERIFY": None,
            "WALLET_VERIFY_BY_INVITE": None,
            "RECEIVE_BTC": self.receive_btc,
            "RECEIVE_ETH": self.receive_eth,
            "RECEIVE_BNB": self.receive_bnb,
            "EDDY_FINANCE_SWAP": self.swap_eddy,
            "RANGE_PROTOCOL_VAULT_TRANSACTION": self.range_vault,
            "ACCUMULATED_FINANCE_DEPOSIT": self.accumulated_finance,
            "ZETA_EARN_STAKE": self.stake_zeta,
            "ZETA_SWAP_SWAP": self.zetaswap,
            "ULTIVERSE_MINT_BADGE": self.ultiverse_badge,
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.success(f'{self.client.account.address} | All tasks done')
        self.session.close()

    def generate_signature(self) -> hex:
        msg = {
            "types": {
                "Message": [{"name": "content", "type": "string"}],
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                ],
            },
            "domain": {"name": "Hub/XP", "version": "1", "chainId": 7000},
            "primaryType": "Message",
            "message": {"content": "Claim XP"},
        }

        encoded_data = encode_typed_data(full_message=msg)
        result = self.client.w3.eth.account.sign_message(encoded_data, self.client.account.key.hex())
        claim_signature = result.signature.hex()

        return claim_signature

    async def enroll(self) -> bool:
        contract_address = '0x3C85e0cA1001F085A3e58d55A0D76E2E8B0A33f9'
        contract = self.client.w3.eth.contract(
            address=self.client.w3.to_checksum_address(contract_address),
            abi=invitation_manager_abi
        )
        if await contract.functions.hasBeenVerified(self.client.account.address).call():
            logger.info(f"{self.client.account.address} | Already enrolled...")
            return True
        await sleep(delay_between_rpc_requests, echo=False)
        ok, tx_hash_or_err = await self.client.send_transaction(
            to=self.client.w3.to_checksum_address(contract_address),
            data=contract.encodeABI('markAsVerified')
        )
        await sleep(delay_between_rpc_requests, echo=False)
        return await self.client.verify_transaction(tx_hash_or_err, 'Enroll')

    async def enroll_verify(self):
        headers = {
            'Origin': 'https://hub.zetachain.com',
            'Referer': 'https://hub.zetachain.com/'
        }
        while True:
            try:
                response = await self.session.post(
                    "https://xp.cl04.zetachain.com/v1/enroll-in-zeta-xp",
                    json={"address": self.client.account.address},
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"{self.client.account.address} | Verify enroll status: {data['isUserVerified']}")
                return True
            except RequestsError:
                logger.warning(f'{self.client.account.address} | Couldn\'t verify enroll - {response.text}')
                await sleep(600, 800)

    async def ultiverse_badge(self):
        async def get_mint_data():
            headers = {
                'Origin': 'https://mission.ultiverse.io',
                'Referer': 'https://mission.ultiverse.io/',
                'Ul-Auth-Api-Key': 'bWlzc2lvbl9ydW5uZXJAZFd4MGFYWmxjbk5s'
            }
            response = await self.session.post(
                'https://toolkit.ultiverse.io/api/user/signature',
                json={"address": self.client.account.address, 'chainId': 1, 'feature': "assets-wallet-login"},
                headers=headers
            )
            data = response.json()
            message = data['data']['message']
            signature = self.client.w3.eth.account.sign_message(
                encode_defunct(text=message),
                private_key=self.client.account.key.hex()
            ).signature.hex()
            response = await self.session.post(
                'https://toolkit.ultiverse.io/api/wallets/signin',
                json={"address": self.client.account.address, 'chainId': 1, 'signature': signature},
                headers=headers
            )
            data = response.json()
            auth_token = data['data']['access_token']
            response = await self.session.post(
                "https://mission.ultiverse.io/api/tickets/mint",
                json={"address": self.client.account.address, 'eventId': 10},
                headers={'Ul-Auth-Token': auth_token, **headers},
                cookies={'Ultiverse_Authorization': auth_token}
            )
            data = response.json()
            return data['data']

        mint_data = await get_mint_data()
        contract = self.client.w3.eth.contract(
            address=self.client.w3.to_checksum_address(mint_data['contract']),
            abi=ultiverse_badge_abi,
        )
        ok, tx_hash_or_err = await self.client.send_transaction(
            to=contract.address,
            data=contract.encodeABI('buy', args=[
                mint_data['expireAt'], mint_data['tokenId'], mint_data['eventId'], mint_data['signature']
            ])
        )
        if await self.client.verify_transaction(tx_hash_or_err, 'Mint a badge on Ultiverse'):
            logger.success(f'{self.client.account.address} | "Mint a badge on Ultiverse" task done. Need to claim')

    async def zetaswap(self):
        async def get_swap_data():
            headers = {
                'Api_key': '7e5e5cc85bb10c1a7c5b2836b55e00acfe0a9509',
                'Apikey': '7e5e5cc85bb10c1a7c5b2836b55e00acfe0a9509',
                'Origin': 'https://app.zetaswap.com',
                'Referer': 'https://app.zetaswap.com/'
            }
            amount = random.randrange(TokenAmount(0.000001).Wei, TokenAmount(0.001).Wei)
            params = {
                'src_chain': 'zetachain', 'dst_chain': 'zetachain',
                'token_in': zeta_token_address,
                'token_out': random.choice(zrc20_tokens),
                'amount': TokenAmount(amount, wei=True).Ether,
                'address': self.client.account.address,
                'slippage': 2
            }
            while True:
                response = await self.session.get(
                    'https://newapi.native.org/v1/firm-quote',
                    params=params,
                    headers=headers
                )
                try:
                    response.raise_for_status()
                    data = response.json()
                    if 'error' in data:
                        amount *= 10
                        if amount >= 0.1:
                            params['amount'] = TokenAmount(random.randrange(TokenAmount(0.001).Wei), wei=True).Ether
                        continue
                    return data['txRequest']
                except (RequestsError, KeyError) as e:
                    logger.warning(
                        f'{self.client.account.address} | Couldn\'t get response from app.zetaswap.com - {e.args[0]}'
                    )
                    await sleep(30)

        tx_data = await get_swap_data()
        ok, tx_hash_or_err = await self.client.send_transaction(
            to=tx_data['target'],
            data=tx_data['calldata'],
            value=int(tx_data['value'])
        )
        if await self.client.verify_transaction(tx_hash_or_err, 'Swap on ZetaSwap'):
            logger.success(
                f'{self.client.account.address} | '
                f'"Swap ETH.ETH to WZETA or vice-versa on ZetaSwap" task done. Need to claim'
            )

    async def receive_and_transfer(self):
        ok, tx_hash_or_err = await self.client.send_transaction(
            to=self.client.account.address,
            value=self.client.w3.to_wei(0, "ether")
        )
        await sleep(delay_between_rpc_requests, echo=False)
        if await self.client.verify_transaction(tx_hash_or_err, 'Self transfer'):
            logger.success(
                f'{self.client.account.address} | '
                f'"Send ZETA in ZetaChain" and "Receive ZETA in ZetaChain" tasks done. Need to claim'
            )

    async def receive_bnb(self) -> None:
        bsc_client = Client(BNB, account=self.client.account)
        if (await bsc_client.get_native_balance()).Ether == 0:
            return
        await sleep(delay_between_rpc_requests, echo=False)
        ok, tx_hash_or_err = await bsc_client.send_transaction(
            to=bsc_client.w3.to_checksum_address('0x70e967acFcC17c3941E87562161406d41676FD83'),
            value=random.randint(10 ** 9, 10 ** 10)
        )
        await sleep(delay_between_rpc_requests, echo=False)
        if not ok:
            return
        if await bsc_client.verify_transaction(tx_hash_or_err, 'BSC task'):
            logger.success(f'{self.client.account.address} | "Receive BNB in ZetaChain" task done. Need to claim')

    async def lp_pool(self):
        if not await self.client.approve(
                token_address=bnb_zeta_token_address,
                spender='0x2ca7d64A7EFE2D62A725E2B35Cf7230D6677FfEe',
                abi=self.client.token_abi,
                amount=TokenAmount(0.0001).Wei  # bnb
        ):
            return
        await sleep(delay_between_rpc_requests, echo=False)
        contract = self.client.w3.eth.contract(
            address=self.client.w3.to_checksum_address("0x2ca7d64A7EFE2D62A725E2B35Cf7230D6677FfEe"),
            abi=pool_abi,
        )
        while True:
            bnb_amount = random.randint(1, 1000)
            nonce = await self.client.nonce()
            await sleep(delay_between_rpc_requests, echo=False)
            gas_price = await self.client.w3.eth.gas_price
            await sleep(delay_between_rpc_requests, echo=False)
            ts = (await self.client.w3.eth.get_block("latest"))['timestamp'] + 3600 + delay_between_rpc_requests
            await sleep(delay_between_rpc_requests, echo=False)
            tx = await contract.functions.addLiquidityETH(
                self.client.w3.to_checksum_address(bnb_zeta_token_address),
                bnb_amount,
                0,
                0,
                self.client.account.address,
                ts,
            ).build_transaction(
                {
                    "from": self.client.account.address,
                    "value": TokenAmount(bnb_price / zeta_price * float(TokenAmount(bnb_amount, wei=True).Ether)).Wei,
                    "nonce": nonce,
                    "gasPrice": gas_price,
                    "chainId": 7000,
                }
            )
            await sleep(delay_between_rpc_requests, echo=False)
            try:
                tx["gas"] = int(await self.client.w3.eth.estimate_gas(tx))
            except ContractLogicError as e:
                logger.warning(
                    f'{self.client.account.address} | Couldn\'t estimate gas for Pool deposit transaction. Trying again'
                )
                continue
            await sleep(delay_between_rpc_requests, echo=False)
            signed_txn = self.client.w3.eth.account.sign_transaction(tx, self.client.account.key.hex())
            transaction_hash = (await self.client.w3.eth.send_raw_transaction(signed_txn.rawTransaction)).hex()
            await sleep(delay_between_rpc_requests, echo=False)
            if await self.client.verify_transaction(transaction_hash, 'Pool deposit'):
                logger.success(f'{self.client.account.address} | "LP any core pool" task done. Need to claim')
                return

    async def receive_btc(self):
        contract_for_encoding = self.client.w3.eth.contract(
            address=self.client.w3.to_checksum_address("0x8Afb66B7ffA1936ec5914c7089D50542520208b8"),
            abi=encoding_contract_abi,
        )
        main_contract = self.client.w3.eth.contract(
            address=self.client.w3.to_checksum_address("0x34bc1b87f60e0a30c0e24FD7Abada70436c71406"),
            abi=multicall_abi,
        )
        zeta_amount = random.randint(10 ** 15, 10 ** 16)
        encoded_data = contract_for_encoding.encodeABI(
            fn_name="swapAmount",
            args=[
                (
                    b"_\x0b\x1a\x82t\x9c\xb4\xe2'\x8e\xc8\x7f\x8b\xf6\xb6\x18\xdcq\xa8\xbf\x00'\x10|\x8d\xda\x80\xbb\xbe\x12T\xa7\xaa\xcf2\x19\xeb\xe1H\x1cn\x01\xd7\x00'\x10_\x0b\x1a\x82t\x9c\xb4\xe2'\x8e\xc8\x7f\x8b\xf6\xb6\x18\xdcq\xa8\xbf\x00'\x10\x13\xa0\xc5\x93\x0c\x02\x85\x11\xdc\x02f^r\x85\x13Km\x11\xa5\xf4",
                    self.client.account.address,
                    zeta_amount,
                    3,
                    (await self.client.w3.eth.get_block("latest"))['timestamp'] + 3600 + delay_between_rpc_requests,
                )
            ],
        )
        await sleep(delay_between_rpc_requests, echo=False)
        tx_data = main_contract.encodeABI(fn_name="multicall", args=[[encoded_data, "0x12210e8a"]])
        ok, tx_hash_or_err = await self.client.send_transaction(
            to=self.client.w3.to_checksum_address("0x34bc1b87f60e0a30c0e24FD7Abada70436c71406"),
            value=zeta_amount,
            data=tx_data
        )
        await sleep(delay_between_rpc_requests, echo=False)
        if await self.client.verify_transaction(tx_hash_or_err, 'BTC task'):
            logger.success(f'{self.client.account.address} | "Receive BTC in ZetaChain" task done. Need to claim')

    async def receive_eth(self):
        contract_for_encoding = self.client.w3.eth.contract(
            address=self.client.w3.to_checksum_address("0x8Afb66B7ffA1936ec5914c7089D50542520208b8"),
            abi=encoding_contract_abi,
        )
        main_contract = self.client.w3.eth.contract(
            address=self.client.w3.to_checksum_address("0x34bc1b87f60e0a30c0e24FD7Abada70436c71406"),
            abi=multicall_abi,
        )
        zeta_amount = random.randint(10 ** 14, 10 ** 15)
        encoded_data = contract_for_encoding.encodeABI(
            fn_name="swapAmount",
            args=[
                (
                    b"_\x0b\x1a\x82t\x9c\xb4\xe2'\x8e\xc8\x7f\x8b\xf6\xb6\x18\xdcq\xa8\xbf\x00\x0b\xb8\x91\xd4\xf0\xd5@\x90\xdf-\x81\xe84\xc3\xc8\xceq\xc6\xc8e\xe7\x9f\x00\x0b\xb8\xd9{\x1d\xe3a\x9e\xd2\xc6\xbe\xb3\x86\x01G\xe3\x0c\xa8\xa7\xdc\x98\x91",
                    self.client.account.address,
                    zeta_amount,
                    10,
                    (await self.client.w3.eth.get_block("latest"))['timestamp'] + 3600 + delay_between_rpc_requests,
                )
            ],
        )
        await sleep(delay_between_rpc_requests, echo=False)
        tx_data = main_contract.encodeABI(fn_name="multicall", args=[[encoded_data, "0x12210e8a"]])
        ok, tx_hash_or_err = await self.client.send_transaction(
            to=self.client.w3.to_checksum_address("0x34bc1b87f60e0a30c0e24FD7Abada70436c71406"),
            value=zeta_amount,
            data=tx_data
        )
        await sleep(delay_between_rpc_requests, echo=False)
        if await self.client.verify_transaction(tx_hash_or_err, 'ETH task'):
            logger.success(f'{self.client.account.address} | "Receive ETH in ZetaChain" task done. Need to claim')

    async def stake_zeta(self, amount: int = None) -> bool:
        stZETA_balance = await self.client.balance_of(token_address=stZETA_token_address)
        if amount:
            if stZETA_balance.Wei >= amount:
                logger.info(f'{self.client.account.address} | Already staking {stZETA_balance} stZETA')
                return True
        await sleep(delay_between_rpc_requests, echo=False)
        ok, tx_hash_or_err = await self.client.send_transaction(
            to=stZETA_token_address,
            value=random.randint(10 ** 14, 10 ** 15),
            data='0x5bcb2fc6'
        )
        await sleep(delay_between_rpc_requests, echo=False)
        if await self.client.verify_transaction(tx_hash_or_err, 'Stake ZETA'):
            logger.success(f'{self.client.account.address} | "Complete a stake on ZetaEarn" task done. Need to claim')

    async def range_vault(self):
        # wrap zeta, approve stzeta, approve wzeta, add liquidity

        async def wrap_zeta(amount: int) -> bool:
            WZETA_balance = await self.client.balance_of(token_address=WZETA_token_address)
            if WZETA_balance.Wei >= amount:
                logger.info(f'{self.client.account.address} | Already wrapped {WZETA_balance} WZETA')
                return True
            await sleep(delay_between_rpc_requests, echo=False)
            ok, tx_hash_or_err = await self.client.send_transaction(
                to=WZETA_token_address,
                value=amount,
                data='0xd0e30db0'
            )
            await sleep(delay_between_rpc_requests, echo=False)
            return await self.client.verify_transaction(tx_hash_or_err, 'Wrap ZETA')

        izumi_wzeta_ztzeta_pool_contract = self.client.w3.eth.contract(
            address=izumi_WZETA_stZETA_pool_address,
            abi=izumi_WZETA_stZETA_pool_abi
        )
        pool_balance = await izumi_wzeta_ztzeta_pool_contract.functions.getUnderlyingBalances().call()
        await sleep(delay_between_rpc_requests, echo=False)
        pool_ratio = pool_balance[0] / pool_balance[1]
        stZETA_amount = random.randint(10_000, 100_000)
        WZETA_amount = int(stZETA_amount / pool_ratio)
        stZETA_amount, WZETA_amount, RUNI_amount = await izumi_wzeta_ztzeta_pool_contract.functions.getMintAmounts(
            stZETA_amount, WZETA_amount
        ).call()
        await sleep(delay_between_rpc_requests, echo=False)

        await self.stake_zeta(stZETA_amount)
        await sleep(delay_between_rpc_requests, echo=False)
        await self.client.approve(
            token_address=stZETA_token_address,
            spender=izumi_WZETA_stZETA_pool_address,
            amount=TokenAmount(stZETA_amount, wei=True)
        )
        await sleep(delay_between_rpc_requests, echo=False)

        await wrap_zeta(WZETA_amount)
        await sleep(delay_between_rpc_requests, echo=False)
        await self.client.approve(
            token_address=WZETA_token_address,
            spender=izumi_WZETA_stZETA_pool_address,
            amount=TokenAmount(WZETA_amount, wei=True)
        )
        await sleep(delay_between_rpc_requests, echo=False)

        ok, tx_hash_or_err = await self.client.send_transaction(
            to=izumi_WZETA_stZETA_pool_address,
            data=izumi_wzeta_ztzeta_pool_contract.encodeABI(
                fn_name='mint',
                args=[RUNI_amount, [stZETA_amount, WZETA_amount]]
            )
        )
        await sleep(delay_between_rpc_requests, echo=False)
        if await self.client.verify_transaction(tx_hash_or_err, 'Range pool'):
            logger.success(
                f'{self.client.account.address} | '
                f'FEATURE | "Add liquidity to a ZetaChain Vault on Range" task done. Need to claim'
            )

    async def accumulated_finance(self):
        stZETA_amount = random.randint(10_000, 100_000)

        async def deposit_stZETA():
            stZETAMinter_contract = self.client.w3.eth.contract(
                address=stZETAMinter_address,
                abi=stZETA_minter
            )
            ok, tx_hash_or_err = await self.client.send_transaction(
                to=stZETAMinter_address,
                value=stZETA_amount,
                data=stZETAMinter_contract.encodeABI('deposit', args=[self.client.account.address])
            )
            await sleep(delay_between_rpc_requests, echo=False)
            return await self.client.verify_transaction(tx_hash_or_err, 'Mint stZETA')

        async def deposit_wstZETA():
            wstZETA_contract = self.client.w3.eth.contract(
                address=wstZETA_token_address,
                abi=wstZETA
            )
            ok, tx_hash_or_err = await self.client.send_transaction(
                to=wstZETA_token_address,
                data=wstZETA_contract.encodeABI('deposit', args=[stZETA_amount, self.client.account.address])
            )
            await sleep(delay_between_rpc_requests, echo=False)
            return await self.client.verify_transaction(tx_hash_or_err, 'Stake stZETA')

        await deposit_stZETA()
        await sleep(delay_between_rpc_requests, echo=False)
        await self.client.approve(
            spender=wstZETA_token_address,
            token_address=stZETA_af_token_address,
            amount=stZETA_amount
        )
        await sleep(delay_between_rpc_requests, echo=False)
        if await deposit_wstZETA():
            logger.success(
                f'{self.client.account.address} | '
                f'FEATURE | "Mint and stake stZETA on Accumulated Finance" task done. Need to claim'
            )

    async def swap_eddy(self):
        while True:
            ok, tx_hash_or_err = await self.client.send_transaction(
                to=eddy_swap_address,
                data=f'0x148e6bcc000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
                     f'0000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000'
                     f'020000000000000000000000005f0b1a82749cb4e2278ec87f8bf6b618dc71a8bf000000000000000000000000'
                     f'{random.choice(zrc20_tokens)[2:]}',  # remove 0x
                value=random.randrange(TokenAmount(0.001).Wei)
            )
            await sleep(delay_between_rpc_requests, echo=False)
            if await self.client.verify_transaction(tx_hash_or_err, 'Eddy Swap'):
                logger.success(
                    f'{self.client.account.address} | '
                    f'FEATURE | "Swap any tokens on Eddy Finance" task done. Need to claim'
                )
            return

    async def check_tasks(self) -> tuple[list[str], list[str]]:
        headers = {
            'Origin': 'https://hub.zetachain.com',
            'Referer': 'https://hub.zetachain.com/'
        }
        while True:
            try:
                response = await self.session.get(
                    "https://xp.cl04.zetachain.com/v1/get-user-has-xp-to-refresh",
                    params={"address": self.client.account.address},
                    headers=headers
                )
                response.raise_for_status()
                break
            except RequestsError:
                logger.warning(f'{self.client.account.address} | Couldn\'t check tasks - {response.text}')
                await sleep(600, 800)
        tasks_to_refresh = []
        tasks_to_do = []
        data = response.json()
        for task, task_data in data["xpRefreshTrackingByTask"].items():
            if task_data["hasXpToRefresh"]:
                tasks_to_refresh.append(task)
            elif not task_data["hasAlreadyEarned"]:
                tasks_to_do.append(task)
        return tasks_to_refresh, tasks_to_do

    async def claim_tasks(self) -> list[str]:
        headers = {
            'Origin': 'https://hub.zetachain.com',
            'Referer': 'https://hub.zetachain.com/'
        }
        completed_tasks, available_tasks = await self.check_tasks()
        if not completed_tasks:
            logger.info(f"{self.client.account.address} | Nothing to claim")
        for task in completed_tasks:
            claim_data = {
                "address": self.client.account.address,
                "task": task,
                "signedMessage": self.generate_signature(),
            }
            while True:
                try:
                    response = await self.session.post(
                        "https://xp.cl04.zetachain.com/v1/xp/claim-task",
                        json=claim_data,
                        headers=headers
                    )
                    response.raise_for_status()
                    break
                except RequestsError:
                    logger.warning(f"{self.client.account.address} | Couldn\'t claim {task} task - {response.text}")
                    await sleep(600, 800)
            logger.success(f"{self.client.account.address} | Claimed {task} task")
            await sleep(delay_between_http_requests, echo=False)
        return available_tasks

    async def get_stats(self) -> dict | None:
        headers = {
            'Origin': 'https://hub.zetachain.com',
            'Referer': 'https://hub.zetachain.com/'
        }
        while True:
            try:
                response = await self.session.get(
                    f'https://xp.cl04.zetachain.com/v1/get-points?address={self.client.account.address}',
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                return {'level': data['level'], 'points': data['totalXp'], 'rank': data['rank']}
            except RequestsError:
                logger.warning(f'{self.client.account.address} | Couldn\'t get stats - {response.text}')
                await sleep(600, 800)


async def process_account(key: str, proxy: str) -> dict | None:
    account = Account.from_key(key)
    client = Client(ZetaChain, account=account, proxy=proxy, delay_between_requests=5)
    async with ZetachainHub(client, proxy) as zh:
        logger.info(f'{account.address} | Balance {await client.get_native_balance()} ZETA')
        await zh.enroll()
        await sleep(delay_between_http_requests, echo=False)
        await zh.enroll_verify()
        await sleep(delay_between_http_requests, echo=False)
        available_quests = await zh.claim_tasks()
        logger.info(f'{account.address} | Available tasks: {", ".join(available_quests)}')
        await sleep(delay_between_http_requests, echo=False)
        if choice == 1:
            for task in random.sample(available_quests, len(available_quests)):
                if zh.tasks[task]:
                    await zh.tasks[task]()
                    await sleep(random.uniform(30, 60))
        await zh.claim_tasks()
        logger.success(f'{zh.client.account.address} | All tasks claimed')
        stats = await zh.get_stats()
        return {'address': zh.client.account.address, **stats}


async def main():
    tasks = []
    for key, proxy in zip(private_keys, proxies):
        tasks.append(asyncio.create_task(process_account(key, proxy)))
    stats = await asyncio.gather(*tasks)
    if stats:
        with open('stats.csv', 'w', encoding='utf-8', newline='') as file:
            fieldnames = ['address', 'level', 'points', 'rank']
            writer = csv.DictWriter(file, delimiter=';', fieldnames=fieldnames)
            writer.writeheader()
            for stat in stats:
                if stat:
                    writer.writerow(stat)


if __name__ == "__main__":
    zeta_price, bnb_price = asyncio.run(zeta_and_bnb_price())
    logger.info(f'ZETA: {zeta_price}, BNB: {bnb_price}')
    choice = int(
        input(
            "\n----------------------"
            "\n1: Do tasks"
            "\n2: Claim XP"
            "\n3: Get statistics"
            "\n----------------------"
            "\nChoice: "
        )
    )
    with open("accounts.txt", encoding='utf-8') as file:
        private_keys = [row.strip() for row in file]

    with open("../proxies.txt", encoding='utf-8') as file:
        proxies = [row.strip() for row in file]

    asyncio.run(main())
