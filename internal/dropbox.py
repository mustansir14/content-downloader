import dropbox
import dropbox.files
import requests
import os
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MAX_FILE_SIZE = 150 * 1024 * 1024  # 150 MB

class DropboxClient:

    def __init__(self, app_key: str, app_secret: str, refresh_token: str):
        self.client = dropbox.Dropbox(app_key=app_key, app_secret=app_secret, oauth2_refresh_token=refresh_token)


    def upload_file(self, local_path: str, dropbox_path: str) -> None:
        file_size = os.path.getsize(local_path)
        retry_count = 0
        while True:
            try:
                # if file size is greater than 150 MB, use upload session
                if file_size > MAX_FILE_SIZE:
                    with open(local_path, 'rb') as f:
                        upload_session_start_result = self.client.files_upload_session_start(f.read(MAX_FILE_SIZE))
                        session_id = upload_session_start_result.session_id
                        cursor = dropbox.files.UploadSessionCursor(session_id=session_id, offset=f.tell())
                        commit = dropbox.files.CommitInfo(path=dropbox_path, mode=dropbox.files.WriteMode.overwrite)
                        while f.tell() < file_size:
                            if file_size - f.tell() > MAX_FILE_SIZE:
                                self.client.files_upload_session_append_v2(f.read(MAX_FILE_SIZE), cursor)
                                cursor.offset = f.tell()
                            else:
                                self.client.files_upload_session_finish(f.read(file_size - f.tell()), cursor, commit)
                else:
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
        # check if folder containing the file is empty now, in which case delete folder recursively
        folder_path = os.path.dirname(dropbox_path)
        if folder_path != '/':
            self.__delete_empty_folder_recursively(folder_path)
        
    
    def __delete_empty_folder_recursively(self, folder_path: str) -> None:
        try:
            response = self.client.files_list_folder(folder_path)
            if not response.entries:
                self.client.files_delete_v2(folder_path)
                logging.info(f"Deleted empty folder: {folder_path}")
                one_level_up = os.path.dirname(folder_path)
                if one_level_up != '/':
                    self.__delete_empty_folder_recursively(one_level_up)
        except dropbox.exceptions.ApiError as e:
            logging.error(f"Failed to delete folder {folder_path}: {e}")



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