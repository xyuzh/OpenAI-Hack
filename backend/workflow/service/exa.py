import asyncio
import os

from exa_py import Exa
from exa_py.api import SearchResponse, ResultWithText


class ExaService:
    def __init__(self):
        self.exa = Exa(api_key=os.getenv("EXA_API_KEY"))

    async def search(self, query: str) -> SearchResponse[ResultWithText]:
        return await asyncio.to_thread(self.exa.search_and_contents, query)

    async def crawl(self, url: str) -> SearchResponse[ResultWithText]:
        return await asyncio.to_thread(self.exa.get_contents, url)
