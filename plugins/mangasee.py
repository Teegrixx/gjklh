import json
import re
from typing import List, AsyncIterable
from urllib.parse import urlparse, urljoin, quote_plus

from plugins.client import MangaClient, MangaCard, MangaChapter, LastChapter
from .search_engine import search


class MangaSeeClient(MangaClient):
    base_url = urlparse("https://mangasee123.com/")
    search_url = urljoin(base_url.geturl(), "_search.php")
    manga_url = urljoin(base_url.geturl(), "manga")
    chapter_url = urljoin(base_url.geturl(), "read-online")
    cover_url = "https://cover.nep.li/cover"

    pre_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }

    def __init__(self, *args, name="Mangasee", **kwargs):
        super().__init__(*args, name=name, headers=self.pre_headers, **kwargs)

    def mangas_from_page(self, documents: List):
        names = [doc['s'] for doc in documents]
        url = [f"{self.manga_url}/{doc['i']}" for doc in documents]
        images = [f"{self.cover_url}/{doc['i']}.jpg" for doc in documents]

        mangas = [MangaCard(self, *tup) for tup in zip(names, url, images)]

        return mangas

    def chapter_url_encode(self, chapter):
        chapter = chapter['Chapter']
        Index = ""
        t = chapter[0:1]
        if t != '1':
            Index = "-index-" + t
        n = int(chapter[1:-1])
        m = ""
        a = chapter[-1]
        if a != '0':
            m = "." + a
        return "-chapter-" + str(n) + m + Index + ".html"

    def chapter_display(self, chapter):
        chapter = chapter['Chapter']
        t = int(chapter[1:-1])
        n = chapter[-1]
        return t if n == '0' else str(t) + "." + n

    def chapters_from_page(self, page: bytes, manga: MangaCard = None):

        chap_pat = re.compile(r'vm.Chapters = ([\s\S]*?);')
        chapters_str_list = chap_pat.findall(page.decode())
        if not chapters_str_list:
            return []

        chapter_list = json.loads(chapters_str_list[0])

        index_pat = re.compile(r'vm.IndexName = ([\s\S]*?);')
        index_str_list = index_pat.findall(page.decode())
        if not index_str_list:
            return []

        index_str = json.loads(index_str_list[0])

        for ch in chapter_list:
            if not ch.get('Type'):
                ch['Type'] = 'Chapter'

        links = [f"{self.chapter_url}/{index_str}{self.chapter_url_encode(ch)}" for ch in chapter_list]
        texts = [f"{ch.get('Type')} {self.chapter_display(ch)}" for ch in chapter_list]

        return list(map(lambda x: MangaChapter(self, x[0], x[1], manga, []), zip(texts, links)))

    def updates_from_page(self, page: bytes):

        chap_pat = re.compile(r'vm.LatestJSON = (\[[\s\S]*?]);')
        chapters_str_list = chap_pat.findall(page.decode())
        if not chapters_str_list:
            return []

        chapter_list = json.loads(chapters_str_list[0])

        urls = [f"{self.manga_url}/{ch['IndexName']}" for ch in chapter_list]
        chapter_urls = [f"{self.chapter_url}/{ch['IndexName']}{self.chapter_url_encode(ch)}" for ch in chapter_list]

        urls = dict(zip(urls[:32], chapter_urls[:32]))

        return urls

    def chapterImage(self, ChapterString):
        Chapter = ChapterString[1:-1]
        Odd = ChapterString[-1]
        if Odd == '0':
            return Chapter
        else:
            return Chapter + "." + Odd

    def pageImage(self, PageString):
        s = "000" + str(PageString)
        return s[-3:]

    async def pictures_from_chapters(self, content: bytes, response=None):

        chap_pat = re.compile(r'vm.CurChapter = ([\s\S]*?);')
        chap_str_list = chap_pat.findall(content.decode())
        if not chap_str_list:
            return []

        curChapter = json.loads(chap_str_list[0])

        path_pat = re.compile(r'vm.CurPathName = ([\s\S]*?);')
        path_str_list = path_pat.findall(content.decode())
        if not path_str_list:
            return []

        curPath = json.loads(path_str_list[0])

        index_pat = re.compile(r'vm.IndexName = ([\s\S]*?);')
        index_str_list = index_pat.findall(content.decode())
        if not index_str_list:
            return []

        index_str = json.loads(index_str_list[0])

        pages = list(range(1, int(curChapter['Page']) + 1))

        images_url = [
            f"https://{curPath}/manga/{index_str}/{'' if curChapter['Directory'] == '' else curChapter['Directory'] + '/'}{self.chapterImage(curChapter['Chapter'])}-{self.pageImage(page)}.png"
            for page in pages]

        return images_url

    async def search(self, query: str = "", page: int = 1) -> List[MangaCard]:
        def text_from_document(doc) -> str:
            return doc['s'] + ' ' + ' '.join(doc['a'])

        def title_from_document(doc) -> str:
            return doc['i']

        documents = await search(query=query, page=page, client=self, text_from_document=text_from_document,
                                 title_from_document=title_from_document)

        return self.mangas_from_page(documents)


__plugin__ = MangaSeeClient

