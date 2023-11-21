import os
import requests
import logging
from datetime import datetime, timedelta
import signal
from tqdm import tqdm
import multiprocessing
import glob
import cv2
import numpy as np
import shutil
from dotenv import load_dotenv

# Load configurations from .env file
load_dotenv()
OUTPUT_BASE_PATH = os.getenv("OUTPUT_PATH", "AWF_scrap/dl_frames")

# Configure logging
logging.basicConfig(level=logging.INFO)

# Constants
DURATION = "6h"
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
MAX_TIME = 100


# Helper Functions
def get_output_path():
    """
    Generates a path for saving output based on the current date and time.

    Returns:
        str: A string representing the path where output should be saved, incorporating the current date and time.
    """

    now = datetime.now()
    return os.path.join(OUTPUT_BASE_PATH, now.strftime("%Y_%m_%dT%H_%M_%S"))


def generate_chunks(response):
    """
    Splits the response content into chunks based on a specific delimiter.

    Args:
        response (requests.Response): The HTTP response containing the content to be split.

    Yields:
        bytes: A chunk of the response content, each representing a frame or segment.
    """

    chunks = response.content.split(b"--frame\r\n")
    for chunk in chunks:
        if len(chunk) > 100:
            start = chunk.find(b"\xff\xd8")
            yield chunk[start:]


def handler(signum, frame):
    """
    A signal handler function that raises an exception for timeouts.

    Args:
        signum (int): The signal number.
        frame (frame object): The current stack frame.

    Raises:
        Exception: Custom exception indicating a timeout event.
    """

    raise Exception("Analyze stream timeout")


def download_and_process_images(cameras_ids, output_path):
    """
    Downloads and processes images from camera sources.

    Args:
        cameras_ids (list): A list of camera IDs to download images from.
        output_path (str): The base path where the images will be saved.

    Logs:
        An error message if any exception occurs during the processing of a camera source.
    """

    for source in tqdm(cameras_ids):
        try:
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(MAX_TIME)
            source_path = os.path.join(output_path, source)
            os.makedirs(source_path, exist_ok=True)
            url = f"https://ts1.alertwildfire.org/text/timelapse/?source={source}&preset={DURATION}"
            response = requests.get(url, headers=HEADERS)
            process_camera_images(response, source_path)
            signal.alarm(0)
        except Exception as e:
            logging.error(f"Error processing {source}: {e}")


def process_camera_images(response, source_path):
    """
    Processes camera images from an HTTP response and saves them to a specified path.

    Args:
        response (requests.Response): The HTTP response containing the camera images.
        source_path (str): The path where the images should be saved.

    Logs:
        An error message if any exception occurs during the processing.
    """

    try:
        for i, chunk in enumerate(generate_chunks(response)):
            output_path = os.path.join(source_path, f"{str(i).zfill(8)}.jpg")
            with open(output_path, "wb") as f:
                f.write(chunk)

        # Sort and rename images
        sort_and_rename_images(source_path)
    except Exception as e:
        logging.error(f"Error in processing images for {source_path}: {e}")


def sort_and_rename_images(source_path):
    """
    Sorts and renames images in a given directory based on a time calculation.

    Args:
        source_path (str): The path of the directory containing the images.

    Logs:
        An error message if any exception occurs during the sorting and renaming process.
    """

    try:
        imgs = glob.glob(os.path.join(source_path, "*"))
        imgs.sort()
        nb_imgs = len(imgs)

        if nb_imgs > 0:
            dt = 6 * 60 * 60 / nb_imgs  # Total duration divided by the number of images

            for i, file in enumerate(imgs):
                frame_time = datetime.now() + timedelta(seconds=dt * i)
                frame_name = frame_time.strftime("%Y_%m_%dT%H_%M_%S") + ".jpg"
                new_file = os.path.join(source_path, frame_name)
                shutil.move(file, new_file)
    except Exception as e:
        logging.error(f"Error in sorting and renaming images in {source_path}: {e}")


def remove_if_gray(file):
    """
    Removes an image file if it is determined to be grayscale.

    Args:
        file (str): The path to the image file.

    Logs:
        An error message if any exception occurs, and the file is removed in such cases.
    """

    try:
        im = cv2.imread(file)
        h = im.shape[0]
        im_half = im[h // 2 :, :, :]
        d = np.max(im_half[:, :, 0] - im_half[:, :, 1])
        if d == 0:
            os.remove(file)
    except Exception as e:
        logging.error(f"Error processing file {file}: {e}")
        os.remove(file)


def remove_grayscale_images(output_path):
    """
    Removes grayscale images from a specified directory using multiprocessing.

    Args:
        output_path (str): The base path where the images are stored.

    Logs:
        An error message if any exception occurs during the removal process.
    """

    try:
        imgs = glob.glob(os.path.join(output_path, "**/*.jpg"), recursive=True)
        nb_proc = multiprocessing.cpu_count() - 1
        with multiprocessing.Pool(processes=nb_proc) as pool:
            list(tqdm(pool.imap(remove_if_gray, imgs), total=len(imgs)))
    except Exception as e:
        logging.error(f"Error in removing grayscale images: {e}")


def cleanup_empty_folders(output_path):
    """
    Removes empty folders in a specified directory.

    Args:
        output_path (str): The base path where the folders are located.

    Logs:
        An error message if any exception occurs during the cleanup process.
    """

    try:
        scrap_folders = glob.glob(os.path.join(output_path, "*"))
        for scrap_folder in tqdm(scrap_folders):
            if not os.listdir(scrap_folder):
                shutil.rmtree(scrap_folder)
    except Exception as e:
        logging.error(f"Error cleaning up empty folders: {e}")


# Main Script
if __name__ == "__main__":
    output_path = get_output_path()
    os.makedirs(output_path, exist_ok=True)

    try:
        response = requests.get(CAMERAS_URL, headers=HEADERS)
        cameras_data = response.json()
        cameras_ids = [
            cam["properties"]["id"].lower() for cam in cameras_data["features"]
        ]
        download_and_process_images(cameras_ids, output_path)
        # Remove grayscale images
        remove_grayscale_images(output_path)

        # Cleanup empty folders
        cleanup_empty_folders(output_path)
    except Exception as e:
        logging.error(f"Failed to fetch camera data: {e}")
