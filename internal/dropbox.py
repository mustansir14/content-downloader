import dropbox
import dropbox.files


class DropboxClient:

    def __init__(self, access_token: str):
        self.client = dropbox.Dropbox(access_token)


    def upload_file(self, local_path: str, dropbox_path: str) -> None:
        with open(local_path, 'rb') as f:
            self.client.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)