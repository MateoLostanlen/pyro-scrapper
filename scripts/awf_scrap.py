from pathlib import Path
import requests
import time
import json
import signal
from tqdm import tqdm
from datetime import datetime, timedelta
import multiprocessing
import glob
import cv2
import numpy as np
import os
import shutil
import subprocess

# SCRAP

now = datetime.now()

DURATION = "6h"  # options: 15m, 1h, 3h, 6h, 12h
OUTPUT_PATH = "dl_frames/" + now.isoformat().split(".")[0].replace("-", "_").replace(
    ":", "_"
)
CAMERAS_URL = (
    "https://s3-us-west-2.amazonaws.com/alertwildfire-data-public/all_cameras-v2.json"
)

HEADERS = {
    "Connection": "keep-alive",
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://www.alertwildfire.org/",
    "Host": "s3-us-west-2.amazonaws.com",
}

response = requests.get(CAMERAS_URL, headers=HEADERS)
cameras_data = response.json()
cameras_ids = [cam["properties"]["id"].lower() for cam in cameras_data["features"]]

os.makedirs(OUTPUT_PATH, exist_ok=True)


def generate_chunks(response):
    chunks = response.content.split(b"--frame\r\n")
    for chunk in chunks:
        if len(chunk) > 100:
            start = chunk.find(b"\xff\xd8")
            yield chunk[start:]


def handler():
    raise Exception("Analyze stream timeout")


max_time = 100

for source in tqdm(cameras_ids):
    # try:
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(max_time)
    source_path = os.path.join(OUTPUT_PATH, source)
    os.makedirs(source_path, exist_ok=True)
    url = f"https://ts1.alertwildfire.org/text/timelapse/?source={source}&preset={DURATION}"
    response = requests.get(url, headers=HEADERS)
    for i, chunk in enumerate(generate_chunks(response)):
        output_path = os.path.join(source_path, f"{str(i).zfill(8)}.jpg")
        with open(output_path, "wb") as f:
            f.write(chunk)

    imgs = glob.glob(source_path + "/*")
    imgs.sort()
    nb_imgs = len(imgs)

    dt = 6 * 60 * 60 / nb_imgs

    for i, file in enumerate(imgs):
        frame_time = now + timedelta(seconds=dt * i)
        frame_name = (
            frame_time.isoformat().split(".")[0].replace("-", "_").replace(":", "_")
        )
        new_file = os.path.join(source_path, f"{frame_name}.jpg")
        shutil.move(file, new_file)
    signal.alarm(0)
    # except:
    #     print(f"timeout {source}")


# CLEAN
## drop night images
def remove_if_gray(file):
    im = cv2.imread(file)
    h = im.shape[0]
    im = im[h // 2 :, :, :]
    d = np.max(im[:, :, 0] - im[:, :, 1])
    if d == 0:
        os.remove(file)


imgs = glob.glob(OUTPUT_PATH + "/**/*.jpg")

with multiprocessing.Pool(processes=multiprocessing.cpu_count() - 1) as pool:
    results = tqdm(pool.imap(remove_if_gray, imgs), total=len(imgs))
    tuple(results)


# Run prediction
scrap_folders = glob.glob(OUTPUT_PATH + "/*")
scrap_folders.sort()

weight = "celestial-armadillo-11.pt"

for scrap_folder in tqdm(scrap_folders):
    name = scrap_folder.split("/")[-2] + "_" + scrap_folder.split("/")[-1]

    cmd = f"yolo predict model={weight} conf=0.25 source={scrap_folder} save=False save_txt save_conf name={name}"
    print(f"* Command:\n{cmd}")
    subprocess.call(cmd, shell=True)


# Keep only positive detections
for scrap_folder in tqdm(scrap_folders):
    name = scrap_folder.split("/")[-2] + "_" + scrap_folder.split("/")[-1]
    labels = glob.glob(f"runs/detect/{name}/labels/*")
    labels.sort()
    time_zone = []
    keep = set()
    imgs = glob.glob(scrap_folder + "/*")
    if len(labels) > 0:

        for label in labels:

            t = os.path.basename(label).split(".txt")[0]
            t = datetime.strptime(t, "%Y_%m_%dT%H_%M_%S")
            t_min = t - timedelta(minutes=15)
            t_max = t + timedelta(minutes=15)
            for file in imgs:
                t = os.path.basename(file).split(".jpg")[0]
                t = datetime.strptime(t, "%Y_%m_%dT%H_%M_%S")
                if t > t_min and t < t_max:
                    keep.add(file)

    for file in imgs:
        if not file in keep:
            os.remove(file)

    print(name, len(keep), len(imgs))


## clean empty folders

for scrap_folder in tqdm(scrap_folders):
    if len(glob.glob(scrap_folder + "/*")) == 0:
        shutil.rmtree(scrap_folder)
        name = scrap_folder.split("/")[-2] + "_" + scrap_folder.split("/")[-1]
        shutil.rmtree(f"runs/detect/{name}/labels/")
