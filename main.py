import logging

from internal.content_downloaders.trw import TRWContentDownloader
from internal.dropbox import DropboxClient
from internal.env import Env

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


dropbox_client = DropboxClient(Env.DROPBOX_ACCESS_TOKEN)
downloader = TRWContentDownloader(Env.TRW_EMAIL, Env.TRW_PASSWORD)

logging.info("Starting content download from TRW...")
for content in downloader.get_content():
    logging.info("Downloaded content - %s", content.name)
    dropbox_path = "trw/"
    for key, value in content.hierarchy:
        dropbox_path += f"{key}/{value}/"
    dropbox_path += content.name
    dropbox_client.upload_file(content.path, dropbox_path)
    logging.info("Uploaded content to Dropbox - %s", dropbox_path)