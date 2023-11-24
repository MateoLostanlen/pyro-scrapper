# pyro-scrapper

## Overview
Pyro-Scrapper is a specialized tool designed for scraping images from [Alert Wildfire](https://www.alertwildfire.org/), splitting these images by camera, and preparing them for future analysis using Pyro-Engine (not yet developed). The primary objective of this project is to augment the Pyronear dataset with images of wildfires, which can be either actual fires or false positives, both of which are valuable for analysis.

## Features
- **Image Scraping**: Downloads images from Alert Wildfire, leveraging the `dl_images.py` script. This involves fetching camera data, processing images, and handling various states and timezones. [View Script](https://github.com/MateoLostanlen/pyro-scrapper/blob/main/src/dl_images.py)
- **Image Splitting**: The `split_cams.py` script is used to split images based on the camera they were captured from. It employs OCR techniques to differentiate between static and turning cameras, organizing images accordingly. [View Script](https://github.com/MateoLostanlen/pyro-scrapper/blob/main/src/split_cams.py)
- **Preparation for Pyro-Engine**: Sets the stage for future integration with Pyro-Engine, where predictions and analyses on the scraped images will be performed.

## How It Works
1. **Scraping Images**: The script `dl_images.py` downloads images from Alert Wildfire, categorizing them based on the camera's state and source. It processes the images to ensure they meet the required standards (e.g., removing grayscale images).
2. **Splitting by Camera**: `split_cams.py` takes the downloaded images and splits them into different folders based on whether the camera is static or rotating. This is determined using OCR to read camera coordinates from the images.
3. **Data Preparation**: The final step, which is currently under development, will involve using Pyro-Engine to run predictions on these images to identify wildfires or false positives.

Certainly! Here's the revised Usage section with the added code snippets:

## Installation and Usage
- Clone the repository.
- Ensure you have the required dependencies by installing them from `requirements.txt`.
- Use `docker-compose.yml` for easy setup and deployment.

To start the container, run:
```bash
make run
```

Once the container is running, execute the following commands:

To download images:
```bash
docker exec pyro-scrapper-pyro-scrapper-1 python3 dl_images.py
```

To split images by camera:
```bash
docker exec pyro-scrapper-pyro-scrapper-1 python3 split_cams.py
```

These commands will initiate the image scraping and processing tasks within the Docker container.

## Contributing
Contributions are welcome, especially in the development of the integration with Pyro-Engine for image analysis. Please refer to the `Makefile` for standard procedures in testing and deployment.

## License
The project is open-source and available under a standard license (to be specified by the repository owner).


