## Flow:

# 0. Login
# 1. Get list of courses via algolia search query
# 2. Get course details via masterclass json api (save this as metadata)
# 3. Get media uuid for each chapter and fetch media metadata
# 4. Get m3u8 url for each chapter and download via yt-dlp
import json
import logging
import os
from typing import Dict

import requests
import yt_dlp

from internal.content_downloaders.base import ContentDownloader
from internal.content_downloaders.exceptions import RequestFailedError
from internal.content_downloaders.types import Content

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

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
  'X-Api-Key': "b9517f7d8d1f48c2de88100f2c13e77a9d8e524aed204651acca65202ff5c6cb9244c045795b1fafda617ac5eb0a6c50",
  'Cookie': 'FPC=b359dc1d-8a20-42b1-b791ceecc5d165ef; _cq_duid=1.1751566272.nrF2mYyhpBTbGYFp; _aid=ff60f4d4-1bea-41c9-802f-8c2689461d48; splitter_subject_id=16787615; first_visit=1; first_visit_on=2025-07-03; __stripe_mid=dbd1b025-6f7c-4dd0-b9bd-b6f9219b56fe4f614f; _gcl_au=1.1.1020422061.1751566271.2048493819.1751790096.1751790096; ajs_anonymous_id=next-gen-330cc5a5-92dd-4691-8062-f7e1bdc8c5e8; tatari-cookie-test=70532288; tatari-session-cookie=e521004b-c1f9-c996-fd80-ba0790f9dffe; _sp_id.b501=a6c68450-13c0-4f23-9d05-c1b31dee12b8.1751566273.2.1751790635.1751566277.64d89e08-e990-4c19-9407-a591d00ac488.db034eaa-997f-441a-b8d2-7573c650b593.0aab9e80-4e8b-4d78-9382-2a11369c939c.1751789896277.4; _ga_MXX8KXSBK0=GS2.1.s1751789895$o2$g1$t1751790636$j50$l0$h0; ajs_anonymous_id=next-gen-330cc5a5-92dd-4691-8062-f7e1bdc8c5e8; bogo_available=false; amplitude_idundefinedmasterclass.com=eyJvcHRPdXQiOmZhbHNlLCJzZXNzaW9uSWQiOm51bGwsImxhc3RFdmVudFRpbWUiOm51bGwsImV2ZW50SWQiOjAsImlkZW50aWZ5SWQiOjAsInNlcXVlbmNlTnVtYmVyIjowfQ==; apple_sign_in_state=c5dea1c8-98e9-4e52-aaf1-c171db343c88; _gid=GA1.2.832693664.1752069424; _uetsid=991f28505ccc11f0b4646d4f7a1a4e00; _uetvid=19bc0140583911f0ab521b70d5dca399; _mcl=1; user_membership=AAP; guest_pass_feature_available=true; active_membership=1; ajs_user_id=16787615; _ga_CKM9ZCCQBN=GS2.1.s1752069425$o3$g0$t1752069428$j57$l0$h0; _ga=GA1.2.1302325921.1751566271; track_visit_session_id=c99816cc-dd65-4983-9ff9-768e44be6e3d; __cf_bm=Ffnx1VfqE9BJNMWFkbrKXSPKOjOU0bAPCvUj2GP2jhg-1752073172-1.0.1.1-GmBK4rldDTezj1S7fMfa4DsPP9GcDBR9aGuSSYcFPLK4SW1cf83R.Bl36JL.uTivLYzfOleWB4ByFbx3TN6G2IrfA9KQsQ9pb9mygN8aQ4Y; __stripe_sid=451022da-9f12-47ed-82bd-10edd6b3b4e3f499d4; _gat=1; _ga_TXTKCL3651=GS2.2.s1752073172$o4$g1$t1752073769$j41$l0$h0; muxData=mux_viewer_id=439bd48e-b35b-43a7-ace4-adeacca2e21d&msn=0.04532036301743381&sid=3fad5713-e8e3-4a47-b42b-7a474f5f60ca&sst=1752073171953&sex=1752075278284; amplitude_id_07018da2854fa6ca5b7bab195253250bmasterclass.com=eyJkZXZpY2VJZCI6Im5leHQtZ2VuLTMzMGNjNWE1LTkyZGQtNDY5MS04MDYyLWY3ZTFiZGM4YzVlOCIsInVzZXJJZCI6IjE2Nzg3NjE1Iiwib3B0T3V0IjpmYWxzZSwic2Vzc2lvbklkIjoxNzUyMDczMTcxOTkwLCJsYXN0RXZlbnRUaW1lIjoxNzUyMDczNzc5ODgyLCJldmVudElkIjo2NjEsImlkZW50aWZ5SWQiOjUwLCJzZXF1ZW5jZU51bWJlciI6NzExfQ==; _mc_session=anDHRkoZMMy6mF6Q7fcW8YlsmK4I43AVkrx7Z8PyJovTsCSBqm61jVpJS%2FS%2FvClCkRazoh5essD6dw370e6yEg%2FnN8KyTX7QJwLos%2FVM1QDP2UoRrT2ASvQi%2BFc7eIDqmssdVocjQ0Q4%2FSb1ZcYgpXalQNTwJCLg4hWdyNxm7dLtkHxFQUjYnif5mDONlUVp2kdINRc%2BbXxVNr%2F2cjuVZejqdofTlc774%2FX8XjjmusZxQIrpV6Efs4XIupWJiBTy%2BU%2B%2BtjNKJ2Mk%2FoTGKueV5qkJN3UGhh5Oi2qy24wnKz1riHVs%2F3vB3Y1dpSZwVSqRdTgsEFnQi%2BKcUUxO9wTSqwo4cVlV5hYQx0aYkc4YTMcdwGNojapa0vtD9A4aZrbFyP347tFCIBxB1g9jg%2F%2BT%2F14931SVQuPdwIQqu6dipK0kffVMHyVbW7dweulxxrWAzy0TwVXvaiMAF2jgY064yYQ1kjqTovS2VGul3D1Wn4cMhk5vTO7eqoeu6iFIjSBncPGroIpbCmXkf9%2FHGtDGQ%2Bi%2FinVLcZjX24d1DYYt2NjmPpGIQTiSsHjxs%2BaNQEe%2BI5rnJDZyTLRheaqHiYBNuaXPpb3W1AwzPI73N7LiuSpIrHyMZTM6zE2nZXpT23hf35KH0%2BBOoOazrr4%2BIQTXqEeODmuw4%2BOGFi7oMM6vhdFb6gIhuyrh2fPlj5N7htyEIi%2FCHDCKCZJZgcrHJFQ3Hibd6lYHQVljzMy1vf61Tb7ccoHNJbjp4hVe%2BM5Or5REgYvkiGhicp0lI3HYxzXGyqjvLnnOHbY9pPWD8lyR9%2BFKag25ghB8zIb%2FQC%2Fv--a9%2Bybj8EVi1b%2B1Ag--8YV43FFdHI5nuLWPY4m9OQ%3D%3D'
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
                try:
                    course_details = self.fetch_course_data(course["slug"])
                except RequestFailedError as e:
                    logging.error(f"Failed to fetch course data for {course['slug']}: {e}")
                    continue
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
                    output_path = DOWNLOAD_DIR + f"{chapter['slug']}.mp4"
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
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [],
        'logger': None,
        'noprogress': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([m3u8_url])
