import logging
import os

from internal.content_downloaders.trw import TRWContentDownloader
from internal.dropbox import DropboxClient, DropboxClientUploadError
from internal.utils import sanitize
from internal.env import Env

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

file_handler = logging.FileHandler(Env.LOG_FILE)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
file_logger = logging.getLogger("file_logger")
file_logger.addHandler(file_handler)


dropbox_client = DropboxClient(Env.DROPBOX_APP_KEY, Env.DROPBOX_APP_SECRET, Env.DROPBOX_REFRESH_TOKEN)
downloader = TRWContentDownloader(Env.TRW_EMAIL, Env.TRW_PASSWORD)

logging.info("Starting content download from TRW...")
DROPBOX_BASE_TRW_PATH = "/trw/"
while True:
    existing_files = dropbox_client.list_directory(DROPBOX_BASE_TRW_PATH)
    new_files = []
    for content in downloader.get_content():
        logging.info("Downloaded content - %s", content.name)
        dropbox_path = DROPBOX_BASE_TRW_PATH
        for _, value in content.hierarchy:
            dropbox_path += f"{value.strip()}/"
        dropbox_path += content.name
        dropbox_path = sanitize(dropbox_path)
        new_files.append(dropbox_path)
        try:
            dropbox_client.upload_file(content.path, dropbox_path)
        except DropboxClientUploadError:
            logging.error("Failed to upload content to Dropbox - %s", content.name)
            continue
        logging.info("Uploaded content to Dropbox - %s", dropbox_path)
        file_logger.info(f'{content.file_type.capitalize()} added "{content.name}"\n{os.path.dirname(dropbox_path).replace(DROPBOX_BASE_TRW_PATH, "").replace("/", ">")} GREEN\n')
    
    # delete files that are not in new_files
    for file in existing_files:
        if file not in new_files:
            content_type = "video"
            if file.endswith(".html"):
                content_type = "html"
            elif file.endswith(".json"):
                content_type = "json"
            logging.info("Deleting file from Dropbox - %s", file)
            dropbox_client.delete_file(file)
            file_logger.info(f'{content_type.capitalize()} removed "{os.path.basename(file)}"\n{os.path.dirname(file).replace(DROPBOX_BASE_TRW_PATH, "").replace("/", ">")} RED\n')
