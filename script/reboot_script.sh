#!/bin/bash
# this need to be added to a cron with 
# @reboot bash /home/pi/pyro-scrapper/script/reboot_script.sh

# ssd
mount /dev/sda1 /mnt/T7
chmod 777 /mnt/T7

# run script 
# Path to the virtual environment
VENV_PATH="/home/pi/pyro-scrapper/venv"

# Activate the virtual environment
source "$VENV_PATH/bin/activate"

# Run the Python script
python /home/pi/pyro-scrapper/src/dl_images.py