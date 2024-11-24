"""
Project : MihoyoBBSApkArchive
License : GNU General Public License v3.0

一个下载米游社全部下载APK的脚本

Usage:
    python download_all_apk.py
Options:
    -h, --help      显示帮助信息
    -o, --overwrite 覆盖已存在的APK文件
"""
import os
import logging
import argparse
import concurrent.futures
import re
import httpx
from collections import defaultdict

OVERWRITE_APK = True

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/115.0.0.0 Safari/537.36"}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S')
log = logger = logging


def generate_2x_md(available_versions: list) -> None:
    """
    生成2.x.md文件

    :param available_versions: 可用的版本号列表
    :return: None
    """
    print(available_versions)
    version_pattern = re.compile(r'mihoyobbs_(\d+)\.(\d+)\.\d+')
    grouped_urls = defaultdict(list)

    markdown_part_one = """# 2.x 版本的米游社
    
## 快速跳转
    """
    markdown_part_two = ""
    for url in available_versions:
        match = version_pattern.search(url)
        if match:
            # Extract the second number
            second_number = match.group(2)
            # Check if the second number is a single digit
            if len(second_number) == 1:
                group_key = f"{match.group(1)}.0x"
            else:
                group_key = f"{match.group(1)}.{second_number[0]}x"
            grouped_urls[group_key].append({"version": match.group(0).replace("mihoyobbs_", ""), "url": url})

    for group in sorted(grouped_urls.keys()):
        if group == "1.0x":
            continue
        markdown_part_two += (
            f"\n### {group}版\n\n"
            f"| 版本号 | 下载地址 |\n"
            f"| --- | --- |\n"
        )
        markdown_part_one += f"\n[{group}版本](#{group}版)\n"

        # Sort the version data numerically
        sorted_versions = sorted(
            grouped_urls[group],
            key=lambda v_n: tuple(map(int, v_n["version"].split('.')))
        )

        for v in sorted_versions:
            markdown_part_two += f"| {v['version']} | <{v['url']}> |\n"

    # Write to file
    with open("2.x.md", "w", encoding='utf-8') as f:
        f.write(markdown_part_one + markdown_part_two)


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
    major, minor, _ = url.split("_")[1].split(".")
    series_name = f"{major}.{str(minor)[:-1]}x" if int(minor) >= 10 else f"{major}.x"
    save_path = f"apk/{major}/{series_name}/"
    os.makedirs(save_path, exist_ok=True)

    if not OVERWRITE_APK and os.path.exists(save_path + url.split("/")[-1]):
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

    generate_2x_md(all_available_versions)


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数
    :return: 命令行参数的命名空间
    """
    parser = argparse.ArgumentParser(description="一个下载米游社全部下载APK的脚本")
    parser.add_argument('-o', '--overwrite', action='store_true', help='覆盖已存在的APK文件')
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    user_args = parse_args()
    if user_args.overwrite:
        OVERWRITE_APK = False
    log.info("Starting MihoyoBBS Apk Downloader...")
    download_all_versions()
