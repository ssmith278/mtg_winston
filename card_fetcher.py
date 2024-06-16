import aiohttp
import asyncio
import time
from datetime import timedelta
from ratelimit import limits, sleep_and_retry
from urllib import parse

@sleep_and_retry
@limits(calls=1, period=timedelta(milliseconds=100).total_seconds())
async def fetch_card(name: str, fuzzy: bool):
    # Example call:
    # https://api.scryfall.com/cards/named?set=&fuzzy=Black+Lotus&format=json&face=&version=&pretty=
    
    search_type = 'fuzzy' if fuzzy else 'exact'

    params = {
        search_type: name,
        'format': 'json',
        'face': '',
        'version': '',
        'pretty': ''
    }

    url_args = parse.urlencode(params)

    url = f'https://api.scryfall.com/cards/named?{url_args}'

    card_json = None
    async with aiohttp.ClientSession() as client:
        async with client.get(url) as response:
            print(f'{time.time()} Call to scryfall for card: {name}')
            card_json = await response.json()

    if not card_json:
        return None
    if card_json['object'] == 'error':
        return None
    
    return card_json

def quick_fetch(name: str, fuzzy: bool):
    return asyncio.run(fetch_card(name, fuzzy))