from dataclasses import dataclass, Field
from decimal import Decimal
from typing import Union

from better_automation.discord import DiscordAccount
from better_automation.twitter import TwitterAccount
from eth_account.signers.local import LocalAccount


@dataclass
class DefaultABIs:
    """
    The default ABIs.
    """
    Token = [
        {
            'constant': True,
            'inputs': [],
            'name': 'name',
            'outputs': [{'name': '', 'type': 'string'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [],
            'name': 'symbol',
            'outputs': [{'name': '', 'type': 'string'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [],
            'name': 'totalSupply',
            'outputs': [{'name': '', 'type': 'uint256'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [],
            'name': 'decimals',
            'outputs': [{'name': '', 'type': 'uint256'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [{'name': 'who', 'type': 'address'}],
            'name': 'balanceOf',
            'outputs': [{'name': '', 'type': 'uint256'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': True,
            'inputs': [{'name': '_owner', 'type': 'address'}, {'name': '_spender', 'type': 'address'}],
            'name': 'allowance',
            'outputs': [{'name': 'remaining', 'type': 'uint256'}],
            'payable': False,
            'stateMutability': 'view',
            'type': 'function'
        },
        {
            'constant': False,
            'inputs': [{'name': '_spender', 'type': 'address'}, {'name': '_value', 'type': 'uint256'}],
            'name': 'approve',
            'outputs': [],
            'payable': False,
            'stateMutability': 'nonpayable',
            'type': 'function'
        },
        {
            'constant': False,
            'inputs': [{'name': '_to', 'type': 'address'}, {'name': '_value', 'type': 'uint256'}],
            'name': 'transfer',
            'outputs': [], 'payable': False,
            'stateMutability': 'nonpayable',
            'type': 'function'
        }]


class TokenAmount:
    Wei: int
    Ether: Decimal
    decimals: int

    def __init__(self, amount: Union[int, float, str, Decimal], decimals: int = 18, wei: bool = False) -> None:
        if wei:
            self.Wei: int = amount
            self.Ether: Decimal = Decimal(str(amount)) / 10 ** decimals

        else:
            self.Wei: int = int(Decimal(str(amount)) * 10 ** decimals)
            self.Ether: Decimal = Decimal(str(amount))

        self.decimals = decimals

    def __str__(self) -> str:
        return str(self.Ether)


class Network:
    def __init__(self,
                 name: str,
                 rpc: str,
                 chain_id: int,
                 eip1559_tx: bool,
                 coin_symbol: str,
                 explorer: str,
                 decimals: int = 18,
                 ):
        self.name = name
        self.rpc = rpc
        self.chain_id = chain_id
        self.eip1559_tx = eip1559_tx
        self.coin_symbol = coin_symbol
        self.decimals = decimals
        self.explorer = explorer

    def __str__(self):
        return f'{self.name}'


class DiscordAccountModified(DiscordAccount):
    auth_token: str = Field(default=None, pattern=r"^[A-Za-z0-9+._-]{70}$|^[A-Za-z0-9+._-]{72}$")


class Profile:
    user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    def __init__(
            self,
            twitter: TwitterAccount,
            discord: DiscordAccountModified,
            evm_account: LocalAccount,
            proxy: str = None,
            email: str = None,
            user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ):
        self.twitter = twitter
        self.discord = discord
        self.evm_account = evm_account
        self.proxy = proxy
        self.email = email
        self.user_agent = user_agent

    def __repr__(self):
        return f'Profile({self.twitter}, {self.discord}, {self.evm_account.address}, {self.proxy}, {self.email}, {self.user_agent})'


Ethereum = Network(
    name='ethereum',
    rpc='https://ethereum.publicnode.com',
    chain_id=1,
    eip1559_tx=True,
    coin_symbol='ETH',
    explorer='https://etherscan.io/'
)

Arbitrum = Network(
    name='arbitrum',
    rpc='https://rpc.ankr.com/arbitrum/',
    chain_id=42161,
    eip1559_tx=True,
    coin_symbol='ETH',
    explorer='https://arbiscan.io/',
)

Optimism = Network(
    name='optimism',
    rpc='https://rpc.ankr.com/optimism/',
    chain_id=10,
    eip1559_tx=True,
    coin_symbol='ETH',
    explorer='https://optimistic.etherscan.io/',
)

Polygon = Network(
    name='polygon',
    rpc='https://polygon-rpc.com/',
    chain_id=137,
    eip1559_tx=True,
    coin_symbol='MATIC',
    explorer='https://polygonscan.com/',
)

Avalanche = Network(
    name='avalanche',
    rpc='https://rpc.ankr.com/avalanche/',
    chain_id=43114,
    eip1559_tx=True,
    coin_symbol='AVAX',
    explorer='https://snowtrace.io/',
)

Fantom = Network(
    name='fantom',
    rpc='https://rpc.ankr.com/fantom/',
    chain_id=250,
    eip1559_tx=True,
    coin_symbol='FTM',
    explorer='https://ftmscan.com/',
)

opBNB = Network(
    name='opbnb',
    rpc='https://opbnb.publicnode.com',
    chain_id=204,
    eip1559_tx=True,
    coin_symbol='BNB',
    explorer='https://bscscan.com/'
)

BNB = Network(
    name='bnb',
    rpc='https://binance.llamarpc.com',
    chain_id=56,
    eip1559_tx=True,
    coin_symbol='BNB',
    explorer='https://bscscan.com/'
)
