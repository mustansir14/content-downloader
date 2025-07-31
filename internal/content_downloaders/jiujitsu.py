from bs4 import BeautifulSoup
import cloudscraper
import os
import requests
import urllib.parse

from internal.content_downloaders.base import ContentDownloader
from internal.content_downloaders.exceptions import RequestFailedError, AuthenticationError
from internal.content_downloaders.types import Content
from internal.utils import sanitize

BASE_URL = "https://thejiujitsulifestyle.mykajabi.com"
LOGIN_URL = f"{BASE_URL}/login"
LIBRARY_URL = f"{BASE_URL}/library"
DOWNLOAD_DIR = "downloads/jiujitsu"

class JiuJitsuContentDownloader(ContentDownloader):

    def __init__(self, email: str, password: str):
        self.scraper = cloudscraper.create_scraper(LOGIN_URL)
        res = self.scraper.get(LOGIN_URL)
        if res.status_code != 200:
            raise RequestFailedError("Failed to load login page")
        soup = BeautifulSoup(res.text, 'html.parser')
        authenticity_token = soup.head.find("meta", {"name": "csrf-token"})["content"]
        authenticity_token = urllib.parse.quote_plus(authenticity_token)
        email = urllib.parse.quote_plus(email)
        password = urllib.parse.quote_plus(password)
        payload = f'utf8=%E2%9C%93&authenticity_token={authenticity_token}&member%5Bemail%5D={email}&member%5Bpassword%5D={password}&member%5Bremember_me%5D=1&commit=Sign%20in'
        self.home_page_res = self.scraper.post(LOGIN_URL, data=payload)
        if self.home_page_res.status_code != 200:
            raise AuthenticationError("Failed to log in, check your credentials")

    
    def get_content(self):
        res = self.home_page_res
        page = 1
        while True:
            soup = BeautifulSoup(res.text, 'html.parser')
            products = soup.find_all("div", class_="product-listing")
            if not products:
                break
            for product in products:
                product_name = sanitize(product.h4.text.strip())
                heirarchy = [("products", product_name), ]
                img_source = product.img["src"]
                img_download_path = f"{DOWNLOAD_DIR}/{product_name}.png"
                download_media(img_source, img_download_path)
                yield Content(
                    name=f"{product_name}.png",
                    file_type="image",
                    path=img_download_path,
                    hierarchy=heirarchy
                )
                product_page_href = product.a["href"]
                product_page_res = self.scraper.get(BASE_URL + product_page_href)
                if product_page_res.status_code != 200:
                    raise RequestFailedError(f"Failed to load product page: {product_page_href}")
                products_page_soup = BeautifulSoup(product_page_res.text, 'html.parser')
                categories = products_page_soup.find_all("a", class_="card")
                for category_num, category in enumerate(categories, start=1):
                    category_image_src = category.img["src"]
                    category_name = sanitize(category.h4.text.strip())
                    heirarchy_category = heirarchy + [("categories", f"{category_num}. {category_name}")]
                    category_download_path = f"{DOWNLOAD_DIR}/{category_name}.png"
                    download_media(category_image_src, category_download_path)
                    yield Content(
                        name=f"{category_name}.png",
                        file_type="image",
                        path=category_download_path,
                        hierarchy=heirarchy_category
                    )
                    category_page_href = category["href"]
                    category_page_res = self.scraper.get(category_page_href)
                    if category_page_res.status_code != 200:
                        raise RequestFailedError(f"Failed to load category page: {category_page_href}")
                    videos_page = 1
                    video_num = 1
                    while True:
                        category_page_soup = BeautifulSoup(category_page_res.text, 'html.parser')
                        videos = category_page_soup.find_all("a", class_="post-listing")
                        if not videos:
                            break
                        for video in videos:
                            video_name = sanitize(video.h4.text.strip())
                            video_image_src = video.img["src"]
                            video_image_download_path = f"{DOWNLOAD_DIR}/{video_name}.png"
                            download_media(video_image_src, video_image_download_path)
                            heirarchy_video = heirarchy_category + [("videos", f"{video_num}. {video_name}")]
                            yield Content(
                                name=f"{video_name}.png",
                                file_type="image",
                                path=video_image_download_path,
                                hierarchy=heirarchy_video
                            )
                            video_page_href = BASE_URL + video["href"]
                            video_page_res = self.scraper.get(video_page_href)
                            if video_page_res.status_code != 200:
                                raise RequestFailedError(f"Failed to load video page: {video_page_href}")
                            video_page_soup = BeautifulSoup(video_page_res.text, 'html.parser')
                            video_download_src = video_page_soup.find("div", class_="video-download").a["href"]
                            video_download_path = f"{DOWNLOAD_DIR}/{video_name}.mp4"
                            download_media(video_download_src, video_download_path)
                            yield Content(
                                name=f"{video_name}.mp4",
                                file_type="video",
                                path=video_download_path,
                                hierarchy=heirarchy_video
                            )
                            video_num += 1
                        videos_page += 1
                        category_page_res = self.scraper.get(f"{category_page_href}?page={videos_page}")
                        if category_page_res.status_code != 200:
                            raise RequestFailedError(f"Failed to load category page: {category_page_href}?page={videos_page}")
                    

            

            page += 1
            res = self.scraper.get(f"{LIBRARY_URL}?page={page}")
            



def download_media(url: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)