import glob
import multiprocessing
import os
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from functools import partial  # Make sure to import partial
from multiprocessing import Manager, Pool

from tqdm import tqdm


def filter_by_windows(cam_folder, labels):
    labels.sort()
    keep_labels = set()
    current_list = []
    for idx, file in enumerate(labels):
        match = re.search(r"(\d{4}_\d{2}_\d{2}T\d{2}_\d{2}_\d{2})", file)
        t = datetime.strptime(match.group(), "%Y_%m_%dT%H_%M_%S")
        if len(current_list) == 0:
            last_time = t
            current_list.append(file)
        else:
            if abs((t - last_time).total_seconds()) < 60 * 15:  # 15mn windows
                current_list.append(file)
                last_time = t
            else:
                if len(current_list) > 1:  # min 2 detection on the windows
                    keep_labels = keep_labels.union(set(current_list))

                current_list = [file]
                last_time = t

    if len(current_list) > 1:
        keep_labels = keep_labels.union(set(current_list))

    time_windows = []
    for file in keep_labels:
        match = re.search(r"(\d{4}_\d{2}_\d{2}T\d{2}_\d{2}_\d{2})", file)
        t = datetime.strptime(match.group(), "%Y_%m_%dT%H_%M_%S")
        t_min = t - timedelta(minutes=15)
        t_max = t + timedelta(minutes=15)
        time_windows.append((t_min, t_max))

    imgs = glob.glob(cam_folder + "/*")
    imgs.sort()
    keep_imgs = set()
    for file in imgs:
        match = re.search(r"(\d{4}_\d{2}_\d{2}T\d{2}_\d{2}_\d{2})", file)
        t = datetime.strptime(match.group(), "%Y_%m_%dT%H_%M_%S")
        for t_min, t_max in time_windows:
            if t > t_min and t < t_max:
                keep_imgs.add(file)
                break

    return keep_imgs, keep_labels


def process_camera_folder(cam_folder, weight, conf_model, DONE_FOLDER):
    current_hour = datetime.now().hour
    if current_hour in (19, 1, 7):  # dl times
        print("Main task paused for restricted hours...")

        time.sleep(600)  # sleep 10 mn
    else:
        name = cam_folder.split("/")[-2] + "_" + cam_folder.split("/")[-1]

        cmd = f"yolo predict task=detect model={weight} conf={conf_model} source={cam_folder} save=False save_txt imgsz='(384, 640)' save_conf name={name} project=runs_awf verbose=False"
        print(f"* Command:\n{cmd}")
        subprocess.call(cmd, shell=True)
        labels = glob.glob(f"runs_awf/{name}/labels/*")
        keep_imgs, keep_labels = filter_by_windows(cam_folder, labels)
        if len(keep_imgs):
            save_folder = os.path.join(DONE_FOLDER, name)
            new_img_folder = os.path.join(save_folder, "images")
            os.makedirs(new_img_folder, exist_ok=True)
            new_label_folder = os.path.join(save_folder, "labels")
            os.makedirs(new_label_folder, exist_ok=True)
            for file in keep_imgs:
                new_file = os.path.join(new_img_folder, os.path.basename(file))
                shutil.copy(file, new_file)
            for file in keep_labels:
                new_file = os.path.join(new_label_folder, os.path.basename(file))
                shutil.copy(file, new_file)
            shutil.make_archive(save_folder, "zip", save_folder)
            shutil.rmtree(save_folder)

        shutil.rmtree(cam_folder)
        if len(labels):
            shutil.rmtree(labels[0].split("labels")[0])


def main():
    DL_FRAMES_FOLDER = "/mnt/T7/AWF_scrap/dl_frames"
    DONE_FOLDER = DL_FRAMES_FOLDER.replace("dl_frames", "done")
    weight = "/home/pi/pyro-scrapper/data/model.onnx"
    conf_model = 0.2
    pool_size = 4

    while True:
        folders = glob.glob(f"{DL_FRAMES_FOLDER}/*")
        folders.sort()

        if len(folders):
            cam_folders = glob.glob(f"{folders[0]}/*")

            with Manager() as manager:
                queue = manager.Queue()
                for cam_folder in cam_folders:
                    queue.put(cam_folder)

                # Prepare the partial function with preconfigured arguments
                partial_process = partial(
                    process_camera_folder,
                    weight=weight,
                    conf_model=conf_model,
                    DONE_FOLDER=DONE_FOLDER,
                )

                # Pool of worker processes
                with Pool(pool_size) as pool:
                    # Process the folders as they are available in the queue
                    while not queue.empty():
                        pool.apply_async(partial_process, (queue.get(),))
                    pool.close()  # No more tasks will be submitted to the pool
                    pool.join()  # Wait for the worker processes to exit


if __name__ == "__main__":
    main()
