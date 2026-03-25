# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''
Copyright 2024 Google, LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

	http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
import os
import glob
import fnmatch
import json
from typing import List, Any

try:
    from google.cloud import storage
except ImportError:
    storage = None

DOT_SEPARATOR = '.'

class StorageUtil:
    _gcs_client = None

    @classmethod
    def get_gcs_client(cls):
        if cls._gcs_client is None:
            if storage is None:
                raise ImportError("google-cloud-storage is not installed.")
            cls._gcs_client = storage.Client()
        return cls._gcs_client

    @classmethod
    def is_gcs(cls, path: str) -> bool:
        return path and path.startswith('gs://')

    @classmethod
    def parse_gcs_path(cls, path: str) -> tuple[str, str]:
        path = path[5:]
        parts = path.split('/', 1)
        return parts[0], parts[1] if len(parts) > 1 else ''

    @classmethod
    def read_text(cls, path: str) -> str:
        if cls.is_gcs(path):
            bucket_name, blob_name = cls.parse_gcs_path(path)
            bucket = cls.get_gcs_client().bucket(bucket_name)
            blob = bucket.blob(blob_name)
            return blob.download_as_text()
        else:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()

    @classmethod
    def read_bytes(cls, path: str) -> bytes:
        if cls.is_gcs(path):
            bucket_name, blob_name = cls.parse_gcs_path(path)
            bucket = cls.get_gcs_client().bucket(bucket_name)
            blob = bucket.blob(blob_name)
            return blob.download_as_bytes()
        else:
            with open(path, 'rb') as f:
                return f.read()

    @classmethod
    def write_text(cls, path: str, content: str):
        if cls.is_gcs(path):
            import mimetypes
            content_type = mimetypes.guess_type(path)[0] or 'text/plain'
            bucket_name, blob_name = cls.parse_gcs_path(path)
            bucket = cls.get_gcs_client().bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.upload_from_string(content, content_type=content_type)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

    @classmethod
    def write_bytes(cls, path: str, content: bytes):
        if cls.is_gcs(path):
            import mimetypes
            content_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
            bucket_name, blob_name = cls.parse_gcs_path(path)
            bucket = cls.get_gcs_client().bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.upload_from_string(content, content_type=content_type)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(content)

    @classmethod
    def write_json(cls, path: str, data: Any, indent: int = 2):
        content = json.dumps(data, indent=indent)
        cls.write_text(path, content)

    @classmethod
    def makedirs(cls, path: str, exist_ok: bool = True):
        if not path:
            return
        if cls.is_gcs(path):
            bucket_name, blob_name = cls.parse_gcs_path(path)
            if blob_name:
                if not blob_name.endswith('/'):
                    blob_name += '/'
                bucket = cls.get_gcs_client().bucket(bucket_name)
                blob = bucket.blob(blob_name)
                if not exist_ok and blob.exists():
                    raise FileExistsError(f"Directory {path} already exists")
                if not blob.exists():
                    blob.upload_from_string(b'')
        else:
            os.makedirs(path, exist_ok=exist_ok)

    @classmethod
    def exists(cls, path: str) -> bool:
        if cls.is_gcs(path):
            bucket_name, blob_name = cls.parse_gcs_path(path)
            bucket = cls.get_gcs_client().bucket(bucket_name)
            blob = bucket.blob(blob_name)
            if blob_name.endswith("/") or blob_name == "":
                blobs = list(bucket.list_blobs(prefix=blob_name, max_results=1))
                return len(blobs) > 0
            if blob.exists():
                return True
            blobs = list(bucket.list_blobs(prefix=blob_name + "/", max_results=1))
            return len(blobs) > 0
        else:
            return os.path.exists(path)

    @classmethod
    def join_path(cls, *args) -> str:
        if not args:
            return ""
        if cls.is_gcs(args[0]):
            bucket, prefix = cls.parse_gcs_path(args[0])
            path = prefix
            for arg in args[1:]:
                path = path.rstrip('/') + '/' + str(arg).lstrip('/')
            return f"gs://{bucket}/{path.strip('/')}"
        else:
            return os.path.join(*args)

    @classmethod
    def glob(cls, pattern: str) -> List[str]:
        if cls.is_gcs(pattern):
            bucket_name, blob_prefix = cls.parse_gcs_path(pattern)
            wildcard_idx = blob_prefix.find('*')
            if wildcard_idx == -1:
                return [pattern] if cls.exists(pattern) else []
            
            search_prefix = blob_prefix[:wildcard_idx]
            slash_idx = search_prefix.rfind('/')
            if slash_idx != -1:
                search_prefix = search_prefix[:slash_idx+1]
            else:
                search_prefix = ""
                
            bucket = cls.get_gcs_client().bucket(bucket_name)
            
            # Use delimiter='/' for directory-level searching when the pattern ends with a structure expecting directories.
            # In our case, trips are like gs://bucket/store/date/trip_id.
            blobs = bucket.list_blobs(prefix=search_prefix)
            
            matches = set()
            pattern_parts_len = len(blob_prefix.strip('/').split('/'))
            
            for blob in blobs:
                # To map globs like gs://retailer-exitpass-dev-rrm/7636/*/* to trip directories,
                # we match paths up to the expected depth of the pattern.
                parts = blob.name.strip('/').split('/')
                
                # We only want to match exactly at the prescribed depth to prevent
                # fetching inner subdirectories as root matches
                if len(parts) >= pattern_parts_len:
                    # Construct the sub-path matching the pattern's depth
                    sub_path = '/'.join(parts[:pattern_parts_len])
                    if fnmatch.fnmatch(sub_path, blob_prefix.strip('/')):
                        matches.add(f"gs://{bucket_name}/{sub_path}")
            
            return list(matches)
        else:
            return glob.glob(pattern)

def get_env_file_name(fileName: str) -> str:
    env = os.environ.get('GCP_RETAIL_RUNTIME', 'local')

    envFile = None
    parts = fileName.split(DOT_SEPARATOR)
    if len(parts) == 2:
        tFile = DOT_SEPARATOR.join([parts[0], env, parts[1]])
        if os.path.isfile(tFile):
            envFile = tFile
    
    return envFile


def read_json_file(filepath: str) -> str:
    return StorageUtil.read_text(filepath)


                    