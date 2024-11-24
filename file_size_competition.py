import os
import json


def package_size_is_out_of_control():
    # list all apk in apk folder
    apk_list = []
    for root, dirs, files in os.walk("apk"):
        for file in files:
            if file.endswith(".apk"):
                this_apk = {
                    "version": file.split("_")[1].split(".apk")[0],
                    "size": round(os.path.getsize(os.path.join(root, file)) / (1024 * 1024), 2)
                }
                apk_list.append(this_apk)
    # sort the list
    apk_list.sort(key=lambda x: list(map(int, x["version"].split('.'))))

    # Get package size incremental percentage
    for i in range(1, len(apk_list)):
        apk_list[i]["size_incremental"] = round(
            (apk_list[i]["size"] - apk_list[i - 1]["size"]) / apk_list[i - 1]["size"] * 100, 2)

    # output to json
    with open("apk_size.json", "w") as f:
        json.dump(apk_list, f, indent=2)

if __name__ == '__main__':
    package_size_is_out_of_control()
