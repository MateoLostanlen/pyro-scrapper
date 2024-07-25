import glob
import os
import shutil
from datetime import datetime, timedelta

import numpy as np
from tqdm import tqdm
from ultralytics import YOLO
from dotenv import load_dotenv
import pytz

# Load configurations from .env file
load_dotenv()
OUTPUT_BASE_PATH = os.getenv("OUTPUT_PATH", "AWF_scrap")

DL_FRAMES_FOLDER = f"{OUTPUT_BASE_PATH}/dl_frames"
weight = "/home/pi/pyro-scrapper/data/yolov8s_ncnn_model"
conf_model = 0.1


model = YOLO(weight, task="detect")

# Get the current date in Los Angeles time zone
la_tz = pytz.timezone('America/Los_Angeles')
today_date_la = datetime.now(la_tz).strftime('%Y_%m_%d')

cams = glob.glob(f"{DL_FRAMES_FOLDER}/**/*")
#cams = [cam for cam in cams if today_date_la not in cam]
cams.sort()

for cam in tqdm(cams):
    current_hour = datetime.now().hour
    if current_hour in (19, 1, 7):  # dl times
        break

    imgs = glob.glob(f"{cam}/*.jpg")
    imgs.sort()
    print(cam)

    print("imgs", len(imgs))

    # Inference
    wf_set = set()
    for idx, file in enumerate(imgs):
        results = model(file, imgsz=1024, conf=conf_model, iou=0, verbose=False)
        confidences = results[0].boxes.conf.cpu().numpy()
        if confidences.size > 0:
            wf_set.add(file)

    # Keep wf images
    keep_set = set()
    for idx, file in enumerate(imgs):
        if file in wf_set:
            current_list = set(imgs[max(0, idx - 15) : min(len(imgs) - 1, idx + 15)])
            if (
                len(current_list & wf_set) > 1
            ):  # at least two wf detected on current fire
                keep_set.update(current_list)

    # Save wf images
    processed_cam_folder = cam.replace("dl_frames", "dl_frames_processed")
    os.makedirs(processed_cam_folder, exist_ok=True)
    for file in keep_set:
        new_file = file.replace("dl_frames", "dl_frames_processed")
        shutil.move(file, new_file)

    # Clean
    shutil.make_archive(processed_cam_folder, "zip", processed_cam_folder)
    shutil.rmtree(processed_cam_folder)
    shutil.rmtree(cam)
