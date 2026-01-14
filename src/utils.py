import os
import requests
import uuid
from datetime import datetime


def modify_separator(path, new_sep="/"):
    if os.sep != new_sep:
        return path.replace(os.sep, new_sep)
    return path


def create_tempdir():
    # 生成带时间戳的文件夹名称
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uuid_short = uuid.uuid4().hex[:8]
    temp_dir_name = f"{timestamp}_{uuid_short}"

    # 在当前目录下创建临时文件夹
    temp_dir = os.path.join(".", "temp", temp_dir_name)

    # 创建临时文件夹
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def download_file(url, temp_dir=None):
    if temp_dir is None:
        temp_dir = create_tempdir()

    local_path = os.path.join(temp_dir, os.path.basename(url.split("?")[0]))

    print(f"正在下载: {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(local_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    local_path = modify_separator(local_path)
    print(f"下载完成: {local_path}")
    return local_path
