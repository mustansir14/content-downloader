import json
import logging
import os
import re
import requests
from typing import Dict
from bs4 import BeautifulSoup
import yt_dlp


from internal.content_downloaders.base import ContentDownloader
from internal.content_downloaders.exceptions import RequestFailedError, AuthenticationError
from internal.content_downloaders.types import Content
from internal.utils import sanitize

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

DOWNLOAD_DIR = "downloads/peterson/"

# Base headers shared across requests
BASE_HEADERS = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/json',
    'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'priority': 'u=1, i'
}

# Firebase-specific headers
FIREBASE_HEADERS = {
    **BASE_HEADERS,
    'origin': 'https://petersonacademy.com',
    'sec-fetch-site': 'cross-site',
    'x-client-data': 'CKy1yQEIlbbJAQiktskBCKmdygEIqvXKAQiWocsBCIegzQEIif3OARjh4s4B',
    'x-client-version': 'Chrome/JsCore/11.1.0/FirebaseCore-web',
    'x-firebase-appcheck': 'eyJraWQiOiIwMHlhdmciLCJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxOjI1OTU4MjYwOTQyMTp3ZWI6YTA2NjBiYTFlZGI1MmExNjMzNmQ0NCIsImF1ZCI6WyJwcm9qZWN0c1wvMjU5NTgyNjA5NDIxIiwicHJvamVjdHNcL3BldGVyc29uLWFjYWRlbXktcHJvZCJdLCJwcm92aWRlciI6InJlY2FwdGNoYV9lbnRlcnByaXNlIiwiaXNzIjoiaHR0cHM6XC9cL2ZpcmViYXNlYXBwY2hlY2suZ29vZ2xlYXBpcy5jb21cLzI1OTU4MjYwOTQyMSIsImV4cCI6MTc1NDMxNjEwNCwiaWF0IjoxNzU0MzEyNTA0LCJqdGkiOiJUdXhlWW9KOGhiaXByTGVvRVdVVVhoYUQ3Z2Y0bXdlSkxlSHpIc1MtcjZ3In0.lG-a-c1T-933jdQSyqiKPOvXFy11fL65dYzRZrO-Uycj3tTBwy7vmDU6Ky77Fl6_QKry4EjzUCNX9PNfTSnBu-FkcBQ5VO8hB9V9XuQSF3EhOpXL0L_UskcYE9or81ZcmxhYatnhRpGZcoyYXFZDUuYQEGo5-SvDzMNplQ1qBOMl-jThrwMriX8DEBAaflfyk_WLXVelytOJVaKajE37QSWosHiRN_CDhux79LraCuw3Ocv3Y-Jo6_80VlvI4cJXYLqMkuFttYXnok7jHGx1vxrOBS0dfqzOud8lbFUxwH3op05dP1tWV7SJXHLncI6vsLhKld9A5CAwY301lACmmchaPGYQjG53hzRlwov3pfUGDF9L_UHdTCDdFgkPEjkT93TEkz5H52dDZTOIxRv_8DrsDX_0xuFsN7V1dAlhrxG46Zvrx-CEhUVokT99DL3kAbOfHTQN9EDplvwd5zSqjMNEUDdGZTYyrMzN-fJC8XUy3TNiheY8kvKHVSHgXlTQ',
    'x-firebase-gmpid': '1:259582609421:web:a0660ba1edb52a16336d44'
}

# Session-specific headers
SESSION_HEADERS = {
    **BASE_HEADERS,
    'baggage': 'sentry-environment=production,sentry-release=1.59.1,sentry-public_key=d7f4334237ce7124da211f6ec0171822,sentry-trace_id=c07beee80a5c4d85a3d8acd58b6be454',
    'origin': 'https://petersonacademy.com',
    'referer': 'https://petersonacademy.com/',
    'sec-fetch-site': 'same-origin',
    'sentry-trace': 'c07beee80a5c4d85a3d8acd58b6be454-ae95d7e442ebc547'
}

# Course API headers
COURSE_API_HEADERS = {
    **BASE_HEADERS,
    'baggage': 'sentry-environment=production,sentry-release=1.59.1,sentry-public_key=d7f4334237ce7124da211f6ec0171822,sentry-trace_id=1bb787b82e394c4888cca1dd64efa78e,sentry-transaction=%2F(public)%2Fcourses,sentry-sampled=false,sentry-sample_rand=0.7366658070419645,sentry-sample_rate=0.1',
    'referer': 'https://petersonacademy.com/courses',
    'sec-fetch-site': 'same-origin',
    'sentry-trace': '1bb787b82e394c4888cca1dd64efa78e-b7ddc65ce306b8b4-0'
}

class PetersonContentDownloader(ContentDownloader):
    
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.auth_token = None
        self.session = requests.Session()
        
        # Authenticate immediately
        self._authenticate()
        
    def _authenticate(self):
        """Authenticate with Peterson Academy using Firebase Auth."""
        # Step 1: Get Firebase token
        firebase_url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=AIzaSyAwJFt3rkFI-5Ny7jID_mePeRh9g0AmV3Q"
        
        firebase_data = {
            "returnSecureToken": True,
            "email": self.email,
            "password": self.password,
            "clientType": "CLIENT_TYPE_WEB"
        }
        
        try:
            response = self.session.post(firebase_url, headers=FIREBASE_HEADERS, json=firebase_data)
            response.raise_for_status()
            
            result = response.json()
            if 'idToken' in result:
                self.auth_token = result['idToken']
                logging.info("Successfully obtained Firebase token")
            else:
                raise AuthenticationError("Authentication failed: No token received")
                
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Firebase authentication request failed: {e}")
        except json.JSONDecodeError as e:
            raise AuthenticationError(f"Failed to parse Firebase authentication response: {e}")
        
        # Step 2: Set session cookie
        session_url = "https://petersonacademy.com/api/session-cookie"
        
        session_data = {
            "token": self.auth_token
        }
        
        try:
            response = self.session.post(session_url, headers=SESSION_HEADERS, json=session_data)
            response.raise_for_status()
            
            logging.info("Successfully set session cookie with Peterson Academy")
            
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Session cookie request failed: {e}")
        except json.JSONDecodeError as e:
            raise AuthenticationError(f"Failed to parse session cookie response: {e}")
        
    def get_content(self):
        """
        Retrieves the list of courses from Peterson Academy and fetches their metadata.
        """
        courses_url = "https://petersonacademy.com/courses"

        try:
            # Use the session to make the authenticated request
            response = self.session.get(courses_url, headers=BASE_HEADERS)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all course cards
            course_links = soup.find_all('a', class_='course-card')

            if not course_links:
                return

            # Create download directory
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)            
                        
            logging.info(f"Found {len(course_links)} courses")
            
            for link in course_links:
                course_url = link.get('href')
                
                if course_url:
                    # Extract course slug from href (e.g., "/courses/maps-of-meaning" -> "maps-of-meaning")
                    course_slug = course_url.split('/')[-1]
                    
                    try:
                        # Fetch course metadata
                        course_data = self._fetch_course_data(course_slug)
                        
                        # Save metadata to file
                        filename = f"{course_slug}.json"
                        metadata_file_path = os.path.join(DOWNLOAD_DIR, filename)
                        
                        with open(metadata_file_path, "w") as f:
                            json.dump(course_data, f, indent=4)
                                                                        
                        # Yield metadata as Content
                        yield Content(
                            name=filename,
                            file_type="json",
                            path=metadata_file_path,
                            hierarchy=[("course", course_slug)]
                        )

                        image_url = f"https://ik.imagekit.io/0qkyxdfkk/prod/courses%2F{course_data['id']}%2Fthumb?tr=h-640&alt=media"
                        image_path = os.path.join(DOWNLOAD_DIR, f"{course_slug}.png")

                        # Download course image
                        download_media(image_url, image_path)

                        yield Content(
                            name=f"{course_slug}.png",
                            file_type="image",
                            path=image_path,
                            hierarchy=[("course", course_slug)]
                        )

                        for lesson_num, lesson in enumerate(course_data.get('lessons', []), start=1):
                            lesson_url = "https://petersonacademy.com" + lesson['path']

                            response = self.session.get(lesson_url, headers=BASE_HEADERS)
                            response.raise_for_status()

                            with open("test.html", "w") as f:
                                f.write(response.text)
                            
                            playback_id = extract_playback_id(response.text)
                            if not playback_id:
                                logging.warning(f"No playback ID found for lesson {lesson['title']} in course {course_slug}")
                                continue

                            token = extract_token(response.text)

                            m3u8_url = f"https://stream.mux.com/{playback_id}.m3u8?token={token}&CMCD=cid%3D%22{playback_id}%22%2Csid%3D%222a98f3ba-f411-477c-bf37-cd397fde50eb%22"

                            lesson_name = f"{lesson_num}. {sanitize(lesson['title'])}"
                            output_path = os.path.join(DOWNLOAD_DIR, f"{sanitize(lesson['path'])}.mp4")

                            download_m3u8_with_ytdlp(m3u8_url, output_path)

                            yield Content(
                                name=f"{lesson_name}.mp4",
                                file_type="video",
                                path=output_path,
                                hierarchy=[("course", course_slug)]
                            )
                        
                    except RequestFailedError as e:
                        logging.error(f"Failed to fetch course data for {course_slug}: {e}")
                        continue

        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to retrieve courses page: {e}")
            raise RequestFailedError(f"Failed to retrieve courses page: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred while parsing courses: {e}")
            raise e
    
    def _fetch_course_data(self, course_slug: str) -> Dict:
        """
        Fetches course metadata from the Peterson Academy API.
        """
        url = f"https://petersonacademy.com/api/courses/{course_slug}"
        logging.info(f"Fetching course data for: {course_slug}")
        
        try:
            response = self.session.get(url, headers=COURSE_API_HEADERS)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise RequestFailedError(f"Failed to fetch course data for {course_slug}: {e}")
        except json.JSONDecodeError as e:
            raise RequestFailedError(f"Failed to parse course data for {course_slug}: {e}") 
        

def download_media(url: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def extract_playback_id(text):
    # Define the regex pattern to match the playback ID
    pattern = r'playbackId:\s*"([A-Za-z0-9]+)"'
    
    # Search for the pattern in the given text
    match = re.search(pattern, text)
    
    # Return the playback ID if found, otherwise None
    return match.group(1) if match else None

def extract_token(text):
    # Define the regex pattern to match the playback ID
    pattern = r'playbackData:\{[^}]*token:"([^"]+)"'
    
    # Search for the pattern in the given text
    match = re.search(pattern, text)
    
    # Return the playback ID if found, otherwise None
    return match.group(1) if match else None


def download_m3u8_with_ytdlp(m3u8_url: str, output_path: str):
    """
    Downloads an M3U8 video using yt-dlp.

    Args:
        m3u8_url (str): URL of the .m3u8 stream.
        output_path (str): Desired output file path (e.g., "video.mp4").
    """
    ydl_opts = {
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [],
        'logger': None,
        'noprogress': True,

    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([m3u8_url])