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
OUTPUT_PATH = "/media/mateo/T7/dl_frames/" + now.isoformat().split(".")[0].replace(
    "-", "_"
).replace(":", "_")
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
    try:
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

        if nb_imgs > 0:
            dt = 6 * 60 * 60 / nb_imgs

            for i, file in enumerate(imgs):
                frame_time = now + timedelta(seconds=dt * i)
                frame_name = (
                    frame_time.isoformat()
                    .split(".")[0]
                    .replace("-", "_")
                    .replace(":", "_")
                )
                new_file = os.path.join(source_path, f"{frame_name}.jpg")
                shutil.move(file, new_file)
        signal.alarm(0)
    except:
        print(f"timeout {source}")


# Rewrite
def rewrite(file):
    try:
        im = cv2.imread(file)
        cv2.imwrite(file, im)
    except:
        os.remove(file)


imgs = glob.glob(OUTPUT_PATH + "/**/*.jpg")

nb_proc = multiprocessing.cpu_count() - 1

if nb_proc > 8:
    nb_proc = 8

with multiprocessing.Pool(processes=nb_proc) as pool:
    results = tqdm(pool.imap(rewrite, imgs), total=len(imgs))
    tuple(results)


# CLEAN
## drop night images
def remove_if_gray(file):
    try:
        im = cv2.imread(file)
        h = im.shape[0]
        im_half = im[h // 2 :, :, :]
        d = np.max(im_half[:, :, 0] - im_half[:, :, 1])
        if d == 0:
            os.remove(file)
    except:
        os.remove(file)


imgs = glob.glob(OUTPUT_PATH + "/**/*.jpg")

with multiprocessing.Pool(processes=nb_proc) as pool:
    results = tqdm(pool.imap(remove_if_gray, imgs), total=len(imgs))
    tuple(results)


scrap_folders = glob.glob(OUTPUT_PATH + "/*")
## clean empty folders

for scrap_folder in tqdm(scrap_folders):
    if len(glob.glob(scrap_folder + "/*")) == 0:
        shutil.rmtree(scrap_folder)
        # name = scrap_folder.split("/")[-2] + "_" + scrap_folder.split("/")[-1]
        # shutil.rmtree(f"runs/detect/{name}/labels/")
