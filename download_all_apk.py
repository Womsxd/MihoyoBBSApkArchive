import os
import time
import httpx
import logging

version = [1, 0, 2]
minor_start_code = 0
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S')
log = logger = logging


def get_latest_version() -> str:
    log.info('Get latest version')
    req = httpx.get(
        "https://bbs-api.miyoushe.com/misc/wapi/getLatestPkgVer?channel=miyousheluodi", headers=headers)
    data = req.json()
    log.info(f'Latest version: {data["data"]["version"]}')
    return data["data"]["version"]


def get_version() -> str:
    return ".".join([str(x) for x in version])


def next_version(minor: bool = False) -> None:
    global version, minor_start_code
    if version == [1, 9, 1]:
        # 1.x版本的终结，直接跳入2.x时代
        version = [2, 0, 0]
        log.info(f"Next version: 2.0.0")
        return
    if minor:
        version[1] += 1
        if version[1] == 11:
            # 2.11.1 开始minor更新后第一位为1
            minor_start_code = 1
        version[2] = minor_start_code
    else:
        version[2] += 1
    log.info(f"Next version: {get_version()}")


def get_download_url(latest: bool = True) -> str:
    if latest:
        download_version = get_latest_version()
        mionr = download_version.split(".")[1]
    else:
        download_version = get_version()
        mionr = version[1]
    channel = "miyousheluodi"
    if mionr <= 45:
        # 2.45.1和之前的版本gf为后缀
        channel = "gf"
    return f"https://download-bbs.miyoushe.com/app/mihoyobbs_{download_version}_{channel}.apk"


def check_download_version(download_url: str, client=httpx) -> bool:
    status_code = client.head(download_url).status_code
    if status_code == 404:
        # 简单的判断，404证明文件不存在，返回False
        log.info(f"Version {get_version()} inexistence")
        return False
    return True


def download_apk(download_url: str, save_path: str, client=httpx) -> bool:
    try:
        resp = client.get(download_url)
        with open(save_path+download_url.split("/")[-1], "wb") as f:
            f.write(resp.content)
    except OSError:
        log.error(f"Save version {get_version()} failed")
        return False
    else:
        log.info(f"Download version {get_version()} OK")
        return True


def check_save_path(save_path: str):
    if not os.path.exists(save_path):
        log.info(f"Create directory {save_path}")
        os.makedirs(save_path)


def get_save_path() -> str:
    save_path = f"./apk/{version[0]}/{version[0]}.{version[1]}"
    save_path = f"{save_path[:-1]}x/"
    check_save_path(save_path)
    return save_path


def download_all_versions():
    log.info("Start download all versions")
    latest_version = get_latest_version()
    tow_test = False
    with httpx.Client(headers=headers, http2=True) as client:
        while True:
            time.sleep(2)
            download_url = get_download_url(latest=False)
            if not check_download_version(download_url, client=client):
                # 文件不存在了，就证明minor版本号该下一位了 有些没有.1只有.2的会无法自动处理，可以手动解决
                if tow_test:
                    next_version(minor=True)
                    tow_test = False
                else:
                    next_version()
                    tow_test = True
                continue
            download_apk(download_url, get_save_path(), client=client)
            if get_version() == latest_version:
                break
            next_version()


if __name__ == "__main__":
    log.info("Starting MihoyoBBS Apk Downloader...")
    download_all_versions()
