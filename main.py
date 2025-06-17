import logging

from internal.content_downloaders.trw import TRWContentDownloader
from internal.dropbox import DropboxClient, DropboxClientUploadError
from internal.env import Env

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
        new_files.append(dropbox_path)
        try:
            dropbox_client.upload_file(content.path, dropbox_path)
        except DropboxClientUploadError:
            logging.error("Failed to upload content to Dropbox - %s", content.name)
            continue
        logging.info("Uploaded content to Dropbox - %s", dropbox_path)

    # delete files that are not in new_files
    for file in existing_files:
        if file not in new_files:
            logging.info("Deleting file from Dropbox - %s", file)
            dropbox_client.delete_file(file)
