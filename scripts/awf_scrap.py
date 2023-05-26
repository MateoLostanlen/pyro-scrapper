from pathlib import Path
import requests
import time
import json
import signal
from tqdm import tqdm
from datetime import datetime
import multiprocessing
import glob
import cv2
import numpy as np
import os


# SCRAP

now = datetime.now().isoformat().split('.')[0].replace('-','_').replace(':','_')

DURATION = '6h' # options: 15m, 1h, 3h, 6h, 12h
OUTPUT_PATH = Path("dl_frames/"+now)
CAMERAS_URL = 'https://s3-us-west-2.amazonaws.com/alertwildfire-data-public/all_cameras-v2.json'

HEADERS = {
    'Connection': 'keep-alive',
    'Sec-Fetch-Site': 'same-site',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Referer': 'https://www.alertwildfire.org/',
    'Host': 's3-us-west-2.amazonaws.com'
}

response = requests.get(CAMERAS_URL, headers=HEADERS)
cameras_data = response.json()
cameras_ids = [cam['properties']["id"].lower() for cam in cameras_data["features"]] 

OUTPUT_PATH.mkdir(exist_ok=True)

def generate_chunks(response):
    chunks = response.content.split(b'--frame\r\n')
    for chunk in chunks:
        if len(chunk) > 100:
            start = chunk.find(b'\xff\xd8')
            yield chunk[start:]
            
def handler():
    raise Exception("Analyze stream timeout")
    
max_time = 100

for source in tqdm(cameras_ids):
	try:
		signal.signal(signal.SIGALRM, handler)
		signal.alarm(max_time)
		source_path = OUTPUT_PATH / source
		source_path.mkdir(exist_ok=True)
		url = f'https://ts1.alertwildfire.org/text/timelapse/?source={source}&preset={DURATION}'
		response = requests.get(url, headers=HEADERS)
		for i, chunk in enumerate(generate_chunks(response)):
			output_path = source_path / f"{now}_{str(i).zfill(8)}.jpg"
			with open(output_path, "wb") as f:
			    f.write(chunk)
		time.sleep(5)
		signal.alarm(0)
	except:
		print(f"timeout {source}")


# CLEAN
## drop night images
def remove_if_gray(file):
    im = cv2.imread(file)
    h = im.shape[0]
    im = im[h//2:,:,:]
    d = np.max(im[:,:,0] - im[:,:,1])
    if d==0:
        os.remove(file)

imgs = glob.glob(str(OUTPUT_PATH) + "/**/*.jpg")

with multiprocessing.Pool(processes=multiprocessing.cpu_count()-1) as pool:
    results = tqdm(pool.imap(remove_if_gray, imgs), total=len(imgs))
    tuple(results) 


## clean empty folders

folders = glob.glob(str(OUTPUT_PATH) + "/*")
for folder in folders:
    if len(glob.glob(folder + "/*"))==0:
        os.rmdir(folder)
