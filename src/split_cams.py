import glob
import logging
import os
import re
import shutil
from collections import defaultdict
from datetime import datetime

import pytz
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from dotenv import load_dotenv
from tqdm import tqdm

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Constants
OCR_THRESHOLD = 5
STATIC_CAM_THRESHOLD = 15
BATCH_SIZE = 50
load_dotenv()
OUTPUT_BASE_PATH = os.getenv("OUTPUT_PATH", "AWF_scrap")
DL_FOLDER = os.path.join(OUTPUT_BASE_PATH, "dl_frames")
TIMEZONE = pytz.timezone("America/Phoenix")

# Initialize the OCR model
model = ocr_predictor(
    det_arch="db_resnet50", reco_arch="crnn_vgg16_bn", pretrained=True
).cuda()


def extract_x_value(text):
    # Find all matches of the pattern in the text
    matches = re.findall(r"[Xx]:?[-+]?\d+\.\d+", text)
    # Return the first match converted to float, or -1000 if no match is found
    return float(matches[0].lstrip("xX:")) if matches else -1000


def extract_x_values_from_images(files, model):
    """Extract x values from a list of image files using the OCR model."""
    x_values = []
    try:
        # Load the images as a document
        doc = DocumentFile.from_images(files)

        # Process each page of the document
        for page in doc:
            result = model([page])
            if len(result.pages[0].blocks) == 0:
                x_values.append(-1000)
            else:
                text = ""
                for word in result.pages[0].blocks[-1].lines[0].words:
                    if "Y:" in text or "Z:" in text:
                        break
                    text += word.value.replace("*", "+")
                x_values.append(extract_x_value(text))

    except Exception as e:
        logging.error(f"Error processing OCR batch: {e}")
        x_values.append(-1000)

    return x_values


def group_by_close_values(data, threshold):
    """Group items based on close numerical values."""
    sorted_items = sorted(data.items(), key=lambda x: x[1])
    groups = defaultdict(list)
    group_id = 0

    for i, item in enumerate(sorted_items):
        if i == 0 or abs(item[1] - sorted_items[i - 1][1]) <= threshold:
            groups[group_id].append(item)
        else:
            group_id += 1
            groups[group_id].append(item)

    return groups


# Main Script
if __name__ == "__main__":
    dl_folder = os.path.join(OUTPUT_BASE_PATH, "dl_frames")
    folders = glob.glob(f"{dl_folder}/**/*")
    static_cams, turning_cams = [], []

    timezone = pytz.timezone("America/Phoenix")
    now = datetime.now(TIMEZONE)

    for folder in tqdm(folders, desc="Processing folders"):
        date_str = folder.split("/")[-2]
        date_obj = datetime.strptime(date_str, "%Y_%m_%d")
        if date_obj.date() < now.date():
            img_files = glob.glob(f"{folder}/*.jpg")[:5]  # only on first 5 images
            img_files.sort()
            x_values = extract_x_values_from_images(img_files, model)
            if len(x_values) > 0:
                if (
                    len(x_values) < 2
                    or (max(x_values) - min(x_values)) % 360 < STATIC_CAM_THRESHOLD
                ):
                    static_cams.append(folder)
                else:
                    turning_cams.append(folder)

    # Process static cameras
    for folder in tqdm(static_cams, desc="Processing static cams"):
        new_folder = os.path.join(
            folder.replace("dl_frames", "dl_frames_splited"), "cam_00"
        )
        shutil.move(folder, new_folder)

    # Process turning cameras

    for folder in tqdm(turning_cams, desc="Processing turning cams"):
        img_files = glob.glob(f"{folder}/*.jpg")
        x_values = {}

        for i in range(0, len(img_files), BATCH_SIZE):
            batch = img_files[i : i + BATCH_SIZE]
            batch_x_values = extract_x_values_from_images(batch, model)

            for file, x_value in zip(batch, batch_x_values):
                x_values[file] = x_value

        if x_values:
            grouped = group_by_close_values(x_values, OCR_THRESHOLD)
            for idx, (_, files) in enumerate(grouped.items()):
                new_folder = os.path.join(
                    os.path.dirname(files[0][0]).replace(
                        "dl_frames", "dl_frames_splited"
                    ),
                    f"cam_{str(idx).zfill(2)}",
                )
                _, x = files[0]
                if (
                    len(files) >= 4 and x != "-1000"
                ):  # do not take errors and isolated images
                    os.makedirs(new_folder, exist_ok=True)
                    for file, _ in files:
                        shutil.move(
                            file, os.path.join(new_folder, os.path.basename(file))
                        )
            shutil.rmtree(folder)

    day_folders = glob.glob(f"{dl_folder}/*")
    for day_folder in day_folders:
        if len(glob.glob(f"{day_folder}/*")) == 0:
            shutil.rmtree(day_folder)
