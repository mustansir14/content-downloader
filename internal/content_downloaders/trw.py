import binascii
import json
import logging
import os
from typing import Generator, Dict

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import requests

from internal.content_downloaders.exceptions import AuthenticationError
from internal.content_downloaders.types import Content

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


REQUEST_HEADERS = {
    'sec-ch-ua-platform': '"Linux"',
    'Referer': 'https://app.jointherealworld.com/',
    'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'x-session-token': '',
    'x-connection-id': '8a8efb62-0c53-4ba9-a52c-3bc2f086f4b5',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'content-type': 'application/json'
}

SERVERS = [
    ("Business Mastery", "01GVZRG9K25SS9JZBAMA4GRCEF"),
    ("Social Media", "01GGDHHJJW5MQZBE0NPERYE8E7"),
    ("AI Automation", "01HZFA8C65G7QS2DQ5XZ2RNBFP"),
    ("Hustler's Campus", "01HSRZK1WHNV787DBPYQYN44ZS"),
    ("Ecommerce", "01GGDHHAR4MJXXKW3MMN85FY8C"),
    ("Crypto DeFi", "01GW4K766W7A5N6PWV2YCX0GZP"),
    ("Crypto Trading", "01GW4K82142Y9A465QDA3C7P44"),
    ("Copywriting", "01GGDHGYWCHJD6DSZWGGERE3KZ"),
    ("Content Creation", "01GXNJTRFK41EHBK63W4M5H74M"),
    ("Headquarters", "01GGDHJAQMA1D0VMK8WV22BJJN"),
    ("Crypto Investing", "01GGDHGV32QWPG7FJ3N39K4FME"),
    ("Health & Fitness", "01GVZRNVT519Q67C8BQGJHRDBY"),
]

DOWNLOAD_DIR = "downloads/trw/"

class TRWContentDownloader:

    def __init__(self, email: str, password: str):
        url = "https://eden.therealworld.ag/auth/password/login"

        payload = {
            "email": email,
            "password": password,
            "friendly_name": "chrome on Linux",
            "device_id": "21297c43-80d9-4d26-bc94-bc788680691f",
            "device_type": "Desktop"
        }

        response = self.__request("POST", url, data=payload, auth=False)
        self.auth_headers = REQUEST_HEADERS.copy()
        self.auth_headers['x-session-token'] = response.json()['token']

    
    def get_content(self) -> Generator[Content, None, None]:
        clear_download_dir() # Clear the download directory before starting
        for server_name, server_id in SERVERS:
            server_data = self.fetch_server_data(server_id)
            heirarchy = [("servers", server_name)]
            categories_lookup = server_data["categories_lookup"]
            courses_lookup = server_data["courses_lookup"]
            modules_lookup = server_data["modules_lookup"]
            for category_id in server_data["categories"]:
                category = categories_lookup[category_id]
                heirarchy_category = heirarchy + [("categories", category["title"])]
                for course_num, course_id in enumerate(category["courses"], start=1):
                    course = courses_lookup[course_id]
                    heirarchy_course = heirarchy_category + [("courses", f'{course_num}. {course["title"]}')]
                    if course["embed_link"]:
                        file_path = DOWNLOAD_DIR + f'{course["title"]}.html'
                        download_embed_link(course["embed_link"], file_path)
                        yield Content(
                            file_type="text/html",
                            name=f'{course["title"]}.html',
                            path=file_path,
                            hierarchy=heirarchy_course
                        )
                        delete_media(file_path)
                    for module_num, module_id in enumerate(course["modules"], start=1):
                        module = modules_lookup[module_id]
                        heirarchy_module = heirarchy_course + [("modules", f'{module_num}. {module["title"]}')]
                        for lesson_num, lesson_id in enumerate(module["lessons"], start=1):
                            try:
                                lesson_data = self.fetch_lesson_data(lesson_id)
                                heirarchy_lesson = heirarchy_module + [("lessons", f'{lesson_num}. {lesson_data["title"]}')] 
                                for field in lesson_data["form"]["fields"]:
                                    if field.get("attachment") and field["attachment"].get("properties") and field["attachment"]["properties"].get("downloadUrl"):
                                        download_url = field["attachment"]["properties"]["downloadUrl"]
                                        title = field["title"]
                                        if not title:
                                            title = lesson_data["title"]
                                        filename = f'{lesson_num}. {title}.mp4'
                                        path = DOWNLOAD_DIR + filename
                                        download_video(download_url, path)
                                        yield Content(
                                            name=filename,
                                            file_type="video/mp4",
                                            path=path,
                                            hierarchy=heirarchy_lesson
                                        )
                                        delete_media(path)  # Delete after yielding to save space
                                        field["attachment"] = {"type": "video", "file": filename}
                                with open(DOWNLOAD_DIR + "lesson_data.json", "w") as f:
                                    json.dump(lesson_data, f, indent=4)
                                yield Content(
                                    name="lesson_data.json",
                                    file_type="application/json",
                                    path=DOWNLOAD_DIR + "lesson_data.json",
                                    hierarchy=heirarchy_lesson
                                )
                                delete_media(DOWNLOAD_DIR + "lesson_data.json")  # Delete after yielding to save space
                            except Exception as e:
                                logging.error(f"Error fetching lesson: {str(e)}")
                                continue


    
    def fetch_server_data(self, server_id: str) -> Dict[str, any]:
        url = f"https://rpc.therealworld.ag/api/trpc/school.fetchServerDataCached?input=%7B%22serverId%22%3A%22{server_id}%22%7D"
        response = self.__request("GET", url, auth=True)
        return response.json()["result"]["data"]
    
    def fetch_lesson_data(self, lesson_id: str) -> Dict[str, any]:
        url = f"https://rpc.therealworld.ag/api/trpc/school.retrieveLessonSecure?input=%7B%22lessonId%22%3A%22{lesson_id}%22%7D"
        response = self.__request("GET", url, auth=True)
        encrypted_value = response.json()["result"]["data"]["value"]
        return decrypt_lesson(encrypted_value, self.auth_headers['x-session-token'])


    def __request(self, method: str, url: str, data: dict = None, auth: bool = False) -> requests.Response:
        if auth:
            headers = self.auth_headers
        else:
            headers = REQUEST_HEADERS
        if data is None:
            data = {}

        response = requests.request(method, url, headers=headers, json=data)

        if not response.ok:
            raise AuthenticationError(f"Request failed with status code {response.status_code}: {response.text}")

        return response


def decrypt_lesson(encrypted: str, session_token: str) -> dict:
    # Derive AES key
    key_str = session_token[:32].ljust(32, "0")
    key_bytes = key_str.encode("utf-8")

    # Split the encrypted value
    iv_hex, data_hex = encrypted.split(":")
    iv = binascii.unhexlify(iv_hex)
    ciphertext = binascii.unhexlify(data_hex)

    # AES-CBC decryption
    cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()

    # Remove PKCS7 padding
    padding_len = decrypted_padded[-1]
    decrypted = decrypted_padded[:-padding_len]

    # Decode JSON
    return json.loads(decrypted.decode("utf-8"))



def download_video(url: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def delete_media(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)


def clear_download_dir() -> None:
    if os.path.exists(DOWNLOAD_DIR):
        for filename in os.listdir(DOWNLOAD_DIR):
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)



def download_embed_link(embed_link: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    res = requests.get(embed_link, headers=REQUEST_HEADERS)
    if res.status_code != 200:
        raise Exception(f"Failed to download embed link: {res.status_code} - {res.text}")
    # save as html
    with open(output_path, 'wb') as f:
        f.write(res.content)