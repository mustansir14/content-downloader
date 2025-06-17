import dropbox
import dropbox.files
import requests


class DropboxClient:

    def __init__(self, app_key: str, app_secret: str, refresh_token: str):
        self.client = dropbox.Dropbox(app_key=app_key, app_secret=app_secret, oauth2_refresh_token=refresh_token)


    def upload_file(self, local_path: str, dropbox_path: str) -> None:
        retry_count = 0
        while True:
            try:
                with open(local_path, 'rb') as f:
                    self.client.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
                break
            except requests.exceptions.ConnectionError:
                retry_count += 1
                if retry_count > 3:
                    raise DropboxClientUploadError("Failed to upload file after multiple retries.")
                

    def list_directory(self, dropbox_path: str) -> list:
        files = []
        response = self.client.files_list_folder(dropbox_path, recursive=True) 
        files.extend([entry.path_display for entry in response.entries if type(entry) == dropbox.files.FileMetadata])
        while response.has_more:
            response = self.client.files_list_folder_continue(response.cursor)
            files.extend([entry.path_display for entry in response.entries if type(entry) == dropbox.files.FileMetadata])
        return files
    
    def delete_file(self, dropbox_path: str) -> None:
        self.client.files_delete_v2(dropbox_path)


class BaseDropboxClientException(Exception):
    """Base exception for Dropbox client errors."""
    pass

class DropboxClientUploadError(BaseDropboxClientException):
    """Exception raised when an upload to Dropbox fails."""



# helper function to get a refresh token
def get_refresh_token():
    import requests
    from requests.auth import HTTPBasicAuth

    from internal.env import Env

    APP_KEY = Env.DROPBOX_APP_KEY
    APP_SECRET = Env.DROPBOX_APP_SECRET
    CODE = ''  # from the redirect

    response = requests.post(
        'https://api.dropboxapi.com/oauth2/token',
        auth=HTTPBasicAuth(APP_KEY, APP_SECRET),
        data={
            'code': CODE,
            'grant_type': 'authorization_code',
            'redirect_uri': 'http://localhost'  # must match above
        }
    )

    print(response.json())