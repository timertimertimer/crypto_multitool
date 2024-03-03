import asyncio

import aiosqlite

__all__ = [
    'create_table',
    'get_token',
    'insert_record',
    'update_chips',
    'update_total_points'
]


def execute(func):
    async def wrapper(*args, **kwargs):
        async with aiosqlite.connect("reiki.db") as db:
            cursor = await db.cursor()
            await cursor.execute(await func(*args, **kwargs))
            await db.commit()
            record = await cursor.fetchone()
            return record[0] if record else record

    return wrapper


@execute
async def create_table():
    return ('''
            CREATE TABLE IF NOT EXISTS tokens (
                profile_id INT NOT NULL,
                bearer_token text NOT NULL,
                chips INT,
                pieces INT,
                total REAL,
                UNIQUE (profile_id)
            )
        ''')


@execute
async def get_token(profile_id: int) -> str:
    return f'SELECT bearer_token FROM tokens WHERE profile_id = \'{profile_id}\''


@execute
async def insert_record(profile_id: int, bearer_token: str):
    return f'INSERT OR REPLACE INTO tokens (profile_id, bearer_token) VALUES (\'{profile_id}\', \'{bearer_token}\')'


@execute
async def update_total_points(profile_id: int, points: float):
    return f'UPDATE tokens SET total = {points} WHERE profile_id = {profile_id}'


@execute
async def update_chips(profile_id: int, chips: int, pieces: int):
    return f'UPDATE tokens SET chips = {chips}, pieces = {pieces} WHERE profile_id = {profile_id}'


async def main():
    print(await get_token(1))


if __name__ == '__main__':
    asyncio.run(main())
