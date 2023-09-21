from tqdm import tqdm
from datetime import datetime, timedelta
import multiprocessing
import glob
import os
import shutil
import subprocess


OUTPUT_PATH = "/media/mateo/EXTERNAL_US/dl_frames"
DONE_folder = "/home/mateo/pyronear/dataset/scrapping/pyro-scrapper/done"


neighbour_mode = "idx"
neighbour_mode = "time"


scrap_folders = glob.glob(OUTPUT_PATH + "/**/*")
scrap_folders.sort()

weight = "legendary-field-19.pt"

for scrap_folder in tqdm(scrap_folders):
    try:
        name = scrap_folder.split("/")[-2] + "_" + scrap_folder.split("/")[-1]

        cmd = f"yolo predict model={weight} conf=0.2 source={scrap_folder} save=False save_txt save_conf name={name}"
        print(f"* Command:\n{cmd}")
        subprocess.call(cmd, shell=True)


        labels = glob.glob(f"runs/detect/{name}/labels/*")
        labels.sort()
        time_zone = []
        keep = set()
        imgs = glob.glob(scrap_folder + "/*")
        if len(labels) > 0:

            for label in labels:

                if neighbour_mode == "idx":

                    temp = imgs[0]
                    temp = temp.split(temp.split('_')[-1])[0]

                    for label in labels:
                        idx = int(label.split('_')[-1].split('.')[0])
                        idx_min = max(idx-15,0)
                        idx_max = min(idx+15,360)

                        for i in range(idx_min, idx_max):
                            keep.add(temp + str(i).zfill(8) + ".jpg")

                else:

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

        if len(keep)==0:

            shutil.rmtree(scrap_folder)
            name = scrap_folder.split("/")[-2] + "_" + scrap_folder.split("/")[-1]
            if os.path.isdir(f"runs/detect/{name}/labels/"):
                shutil.rmtree(f"runs/detect/{name}/labels/")

        else:
            os.makedirs(os.path.join(DONE_folder, "images"), exist_ok=True)
            os.makedirs(os.path.join(DONE_folder, "labels"), exist_ok=True)
            #zip images
            
            img_zip = os.path.join(DONE_folder, "images", name)
            shutil.make_archive(img_zip, "zip", scrap_folder)
            shutil.rmtree(scrap_folder)
            # zip labels
            
            label_folder = f"runs/detect/{name}/labels"
            label_zip = os.path.join(DONE_folder, "labels", name)
            shutil.make_archive(label_zip, "zip", label_folder)
            shutil.rmtree(label_folder)

    except:
        # shutil.make_archive(scrap_folder, "zip", scrap_folder)
        # shutil.rmtree(scrap_folder)
        # new_folder = scrap_folder.replace("dl_frames","bugs")
        # shutil.move(f"{scrap_folder}.zip", f"{new_folder}.zip")
        print("bugs", scrap_folder)
    
