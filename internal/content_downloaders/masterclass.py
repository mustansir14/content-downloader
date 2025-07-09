## Flow:

# 0. Login
# 1. Get list of courses via algolia search query
# 2. Get course details via masterclass json api (save this as metadata)
# 3. Get media uuid for each chapter and fetch media metadata
# 4. Get m3u8 url for each chapter and download via yt-dlp
import json
import os
from typing import Dict

import requests
import yt_dlp

from internal.content_downloaders.base import ContentDownloader
from internal.content_downloaders.exceptions import RequestFailedError
from internal.content_downloaders.types import Content

REQUEST_HEADERS = {
  'accept': 'application/json',
  'accept-language': 'en-US,en;q=0.9',
  'content-type': 'application/json',
  'priority': 'u=1, i',
  'referer': 'https://www.masterclass.com/',
  'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Linux"',
  'sec-fetch-dest': 'empty',
  'sec-fetch-mode': 'cors',
  'sec-fetch-site': 'same-origin',
  'traceparent': '00-399a2888eb49951e66282cb96c4ae478-3d6146e64a2ee600-01',
  'tracestate': '981762@nr=0-1-981762-8342478-3d6146e64a2ee600----1751792934053',
  'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
  'Cookie': '__cf_bm=s7bPzt4.BX4uogHG.Zo0UW7bf1b4LY6hmCXC5LOmAmk-1751792974-1.0.1.1-F2APWGBz3KK6Zdzfgefuj7RPNh71OxUc3OmMU8ZqxBaxwYXBFcTuqoODQwY4fezYRsh38A_IeS6JyXBruryh9ZE6WOfgob4wTrnCqU5BF0k; _mc_session=i2mBaiDEfJKkPKUcrOLKIMqM%2FEU8MgJnz5%2F9UFeao8yHX7siHkaxmZyXmZDSYyLAE0o6BT%2BjHOSw3Un2F17uCsJFja8WdLrzIvvG1aPc5Ecw9Z5glUP%2FjUjXVTzR8DA3ROpXdonW6rMIieE%2FvTXS28TaFWM0bxaBKBz4AaJtKceT0WL%2FUYWxbASpNaB5ShN6MqnRrzZmtlMQnQVDMPrehibJYHSXBO7jTTI3rGhite8z72f7ZX2gVo3dCo2PxEoOw%2F10ctPE%2F8qko1rGFEkN4X2xLDAWckUmV6XiEUJvQvkuJh2kOQrYRDGc5UJqCMFDzRA0Ql3NwUesRa5hKMlcfww%3D--jQweIRuhz1qV3jtU--vM5dKj4rB8B4M6RnUJ495g%3D%3D; active_membership=0; ajs_anonymous_id=%22rails-gen-8ed84a83-be8c-4856-87c1-e59fe5331779%22'
}

DOWNLOAD_DIR = "downloads/masterclass/"

class MasterClassContentDownloader(ContentDownloader):
        
    def get_content(self):
        algolia_payload = '{"requests":[{"indexName":"library_consumer_index_production","params":"facetingAfterDistinct=true&facets=[\\"content_length_bucket.en-US\\",\\"content_type\\"]&filters=rank.category.slug:none&highlightPostTag=</ais-highlight-0000000000>&highlightPreTag=<ais-highlight-0000000000>&maxFacetHits=100&maxValuesPerFacet=100&page=%s&tagFilters="}]}'
        url = "https://ujjak2x1py-2.algolianet.com/1/indexes/*/queries?x-algolia-agent=Algolia%20for%20JavaScript%20(4.23.3)%3B%20Browser%20(lite)%3B%20JS%20Helper%20(3.14.0)%3B%20react%20(18.3.1)%3B%20react-instantsearch%20(6.40.4)&x-algolia-api-key=ZDA3Y2MwZWNiMmMwNThmODEzNWE5MDQ1NDFkM2I4NjExMGJkYzcyOGFjZWYzM2M2NGVkOTYzODFlOWVjYTRiMmZpbHRlcnM9JTI4aW4lM0FhbGwlMjkrQU5EK05PVCtleCUzQWVudGVycHJpc2U%3D&x-algolia-application-id=UJJAK2X1PY"
        
        total_pages = 13 # initial value, will be updated from requests
        page = 0
        while page < total_pages:
            payload = algolia_payload % page
            response = self.__request("POST", url, payload)
            result = response.json()["results"][0]
            total_pages = result["nbPages"]
            for course in result["hits"]:
                course_details = self.fetch_course_data(course["slug"])
                filename = course_details["slug"] + ".json"
                os.makedirs(DOWNLOAD_DIR, exist_ok=True)
                metadata_file_path = DOWNLOAD_DIR + filename
                with open(metadata_file_path, "w") as f:
                    json.dump(course_details, f, indent=4)
                course_metadata_content = Content(
                    name=filename,
                    file_type="json",
                    path=metadata_file_path,
                    hierarchy=[("course", course_details["slug"])]
                )
                yield course_metadata_content
                for chapter_num, chapter in enumerate(course_details["chapters"], start=1):
                    media_data = self.fetch_media_data(chapter["media_uuid"])
                    m3u8_url = None
                    for source in media_data["sources"]:
                        if source["type"] == "application/x-mpegURL":
                            m3u8_url = source["src"]
                            break
                    if not m3u8_url:
                        raise RequestFailedError(
                            f"No M3U8 URL found for chapter {chapter['title']} in course {course_details['title']}"
                        )
                    output_path = DOWNLOAD_DIR + f"{chapter["slug"]}.mp4"
                    download_m3u8_with_ytdlp(m3u8_url, output_path)
                    yield Content(
                        name= f"{chapter_num}. {chapter['slug']}.mp4",
                        file_type="video",
                        path=output_path,
                        hierarchy=[("course", course_details["slug"])]
                    )



                    
            page += 1


    def fetch_course_data(self, course_slug: str) -> Dict:
        url = f"https://www.masterclass.com/jsonapi/v1/courses/{course_slug}?deep=true"
        response = self.__request("GET", url)
        return response.json()
    

    def fetch_media_data(self, media_uuid: str) -> Dict:
        url = f"https://edge.masterclass.com/api/v1/media/metadata/{media_uuid}"
        response = self.__request("GET", url)
        return response.json()


    def __request(self, method: str, url: str, data: str = None) -> requests.Response:
        response = requests.request(method, url, headers=REQUEST_HEADERS, data=data)

        if not response.ok:
            raise RequestFailedError(
                f"Request failed with status code {response.status_code}: {response.text}")

        return response


    

def download_m3u8_with_ytdlp(m3u8_url: str, output_path: str):
    """
    Downloads an M3U8 video using yt-dlp.

    Args:
        m3u8_url (str): URL of the .m3u8 stream.
        output_path (str): Desired output file path (e.g., "video.mp4").
    """
    ydl_opts = {
        'outtmpl': output_path,
        'format': 'bestvideo+bestaudio',  # video + audio
        'merge_output_format': 'mp4',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([m3u8_url])
