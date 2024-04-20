import re
from dataclasses import dataclass
from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote_plus

from bs4 import BeautifulSoup

from models import MangaCard, MangaChapter
from plugins.client import MangaClient


@dataclass
class ComicKioCard(MangaCard):
    read_url: str

    def get_url(self):
        return self.read_url


class ComicKioClient(MangaClient):
    base_url = urlparse("https://comick.io/")
    search_url = urljoin(base_url.geturl(), "search")
    search_param = 'q'
    home_page = urljoin(base_url.geturl(), "home-page")
    img_server = "https://meo2.comick.pictures/"

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="ComicK.io", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")
        cards = bs.find_all("div", {"class": "comic-item"})
        mangas = []

        for card in cards:
            title = card.find("h3").text.strip()
            url = urljoin(self.base_url.geturl(), card.find("a").get("href"))
            cover_url = urljoin(self.img_server, card.find("img").get("data-src"))
            read_url = urljoin(self.base_url.geturl(), card.find("a").get("href"))
            mangas.append(ComicKioCard(self, title, url, cover_url, read_url))

        return mangas

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):
        bs = BeautifulSoup(page, "html.parser")
        chapters = bs.find_all("a", {"class": "chapter-item"})

        manga_chapters = []
        for chapter in chapters:
            chapter_title = chapter.find("div", {"class": "chapter-title"}).text.strip()
            chapter_url = urljoin(self.base_url.geturl(), chapter.get("href"))
            manga_chapters.append(MangaChapter(self, chapter_title, chapter_url, manga))

        return manga_chapters

    def updates_from_page(self, page: bytes):
        bs = BeautifulSoup(page, "html.parser")
        updates = {}

        manga_items = bs.find_all("div", {"class": "comic-item"})
        for manga_item in manga_items:
            manga_url = urljoin(self.base_url.geturl(), manga_item.find("a").get("href"))
            chapter_item = manga_item.find("div", {"class": "chapter-item"})
            if chapter_item:
                chapter_url = urljoin(self.base_url.geturl(), chapter_item.find("a").get("href"))
                updates[manga_url] = chapter_url

        return updates

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        request_url = self.search_url

        if query:
            request_url = f'{request_url}?{self.search_param}={quote_plus(query)}'

        content = await self.get_url(request_url)

        return self.mangas_from_page(content)[(page - 1) * 20:page * 20]

    async def get_chapters(self, manga_card: MangaCard, page: int = 1) -> List[MangaChapter]:
        request_url = f'{manga_card.url}'

        content = await self.get_url(request_url)

        return self.chapters_from_page(content, manga_card)[(page - 1) * 20:page * 20]

    async def iter_chapters(self, manga_url: str, manga_name) -> AsyncIterable[MangaChapter]:
        manga_card = MangaCard(self, manga_name, manga_url, '')

        request_url = f'{manga_card.url}'

        content = await self.get_url(request_url)

        for chapter in self.chapters_from_page(content, manga_card):
            yield chapter

    async def contains_url(self, url: str):
        return url.startswith(self.base_url.geturl())

    async def check_updated_urls(self, last_chapters: List[LastChapter]):
        content = await self.get_url(self.home_page)

        updates = self.updates_from_page(content)

        updated = [lc.url for lc in last_chapters if updates.get(lc.url) and updates.get(lc.url) != lc.chapter_url]
        not_updated = [lc.url for lc in last_chapters if not updates.get(lc.url)
                       or updates.get(lc.url) == lc.chapter_url]

        return updated, not_updated

    async def get_cover(self, manga_card: MangaCard, *args, **kwargs):
        headers = {**self.pre_headers, 'Referer': self.base_url.geturl()}
        return await super(ComicKioClient, self).get_cover(manga_card, *args, headers=headers, **kwargs)

    async def get_picture(self, manga_chapter: MangaChapter, url, *args, **kwargs):
        headers = {**self.pre_headers, 'Referer': self.base_url.geturl()}
        return await super(ComicKioClient, self).get_picture(manga_chapter, url, *args, headers=headers, **kwargs)
