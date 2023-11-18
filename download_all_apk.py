import os
import logging
import concurrent.futures
import httpx

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/115.0.0.0 Safari/537.36"}
overwrite_apk = True

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S')
log = logger = logging


def get_latest_version() -> str:
    """
    获取当前最新版本的版本号(web api)

    :return: 最新版本的版本号
    """
    log.info('Get latest version')
    req = httpx.get(
        "https://bbs-api.miyoushe.com/misc/wapi/getLatestPkgVer?channel=miyousheluodi",
        headers=headers)
    data = req.json()
    log.info(f'Latest version: {data["data"]["version"]}')
    return data["data"]["version"]


def generate_predicted_version_dict() -> dict:
    """
    生成预测的版本号字典

    :return: 预测的版本号字典
    """
    version_dict = {}
    latest_version = get_latest_version().split(".")
    for major in range(1, int(latest_version[0]) + 1):
        if major == int(latest_version[0]):
            for minor in range(0, int(latest_version[1])):
                k_value = f"{major}.{minor}"
                version_dict[k_value] = list(range(0, 10))
        elif major == 1:
            for minor in range(0, 10):
                k_value = f"{major}.{minor}"
                version_dict[k_value] = list(range(0, 10))
        else:
            for minor in range(0, 100):
                k_value = f"{major}.{minor}"
                version_dict[k_value] = list(range(0, 10))
    return version_dict


def generate_available_version_list(major_minor_str: str, rev_list: list) -> list:
    """
    生成可用的版本号列表

    :param major_minor_str: 版本号字符串
    :param rev_list: 版本号列表
    :return: 可用的版本号列表
    """
    client = httpx.Client(headers=headers, http2=True)
    major, minor = major_minor_str.split(".")
    available_version_num_list = []
    available_version_url_list = []
    downloaded = False
    channel = "gf" if int(minor) <= 45 and int(major) in [1, 2] else "miyousheluodi"
    for rev in rev_list:
        this_version = f"{major_minor_str}.{rev}"
        download_url = f"https://download-bbs.miyoushe.com/app/" \
                       f"mihoyobbs_{this_version}_{channel}.apk"
        resp = client.head(download_url)
        if resp.status_code == 404:
            log.info(f"Version {this_version} not found")
            if downloaded:
                break
            continue
        if resp.status_code == 200:
            log.info(f"Version {this_version} is available")
            available_version_url_list.append(download_url)
            available_version_num_list.append(this_version)
            downloaded = True
        else:
            log.error(f"Version {this_version} unknown error: {resp.status_code}")
    log.info(f"Version {major_minor_str} check finished: {available_version_num_list} are available")
    return available_version_url_list


def download_apk(url: str) -> bool:
    """
    下载apk文件

    :param url: 下载地址
    :return: 下载是否成功
    """
    # check if the file exists already
    apk_file_name = url.split("/")[-1]
    major, minor, rev = url.split("_")[1].split(".")
    series_name = f"{major}.{str(minor)[:-1]}x" if int(minor) >= 10 else f"{major}.x"
    save_path = f"apk/{major}/{series_name}/"
    os.makedirs(save_path, exist_ok=True)

    if not overwrite_apk and os.path.exists(save_path + url.split("/")[-1]):
        log.info(f"{apk_file_name} already exists, skip the download task.")
        return True
    try:
        log.info(f"Start downloading: {url}")
        resp = httpx.get(url, headers=headers)
        with open(save_path + apk_file_name, "wb") as f:
            f.write(resp.content)
    except OSError:
        log.error(f"Save version {apk_file_name} failed")
        return False
    log.info(f"Download version {apk_file_name} OK")
    return True


def download_all_versions() -> None:
    """
    下载所有可用版本

    :return: None
    """
    log.info("Start fetch all versions metadata")
    cpu_count = os.cpu_count()
    all_available_versions = []
    predicted_version_dict = generate_predicted_version_dict()

    with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_count) as executor:
        # Submit version generation tasks to the ThreadPoolExecutor
        version_tasks = {
            executor.submit(generate_available_version_list, major_minor, rev_list): (major_minor, rev_list)
            for major_minor, rev_list in predicted_version_dict.items()
        }

        # Collect results
        for future in concurrent.futures.as_completed(version_tasks):
            available_versions = future.result()
            all_available_versions.extend(available_versions)
    log.info(f"All version checks completed, {len(all_available_versions)} versions are available")

    # Download tasks
    log.info("Start download all available versions")

    with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_count) as executor:
        # Submit download tasks to the ThreadPoolExecutor
        download_tasks = [
            executor.submit(download_apk, v) for v in all_available_versions
        ]

        # Wait for all tasks to complete
        for future in concurrent.futures.as_completed(download_tasks):
            result = future.result()
            if not result:
                log.error("Some downloads failed")


if __name__ == "__main__":
    log.info("Starting MihoyoBBS Apk Downloader...")
    download_all_versions()
