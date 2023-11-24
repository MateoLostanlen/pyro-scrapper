FROM nvidia/cuda:12.2.0-devel-ubuntu22.04

# set environment variables
ENV PYTHONPATH "${PYTHONPATH}:/usr/src/app"
ENV PATH /usr/local/bin:$PATH
ENV LANG C.UTF-8
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# set work directory
WORKDIR /usr/src/app


# install git
RUN apt-get update && apt-get install git -y

COPY ./requirements.txt /tmp/requirements.txt
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    libsm6 \
    libxext6 \
    python3-pip && \
    pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt && \
    pip cache purge && \
    rm -rf /root/.cache/pip /var/lib/apt/lists/*



COPY ./src/dl_images.py /usr/src/app/dl_images.py
COPY ./src/split_cams.py /usr/src/app/split_cams.py
