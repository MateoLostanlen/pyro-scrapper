FROM nvcr.io/nvidia/l4t-ml:r32.7.1-py3


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

RUN apt-get install -y \
    python3-pip && \
    pip3 install --upgrade pip setuptools wheel 



RUN pip3 install protobuf==3.19.1
RUN wget https://nvidia.box.com/shared/static/pmsqsiaw4pg9qrbeckcbymho6c01jj4z.whl -O onnxruntime_gpu-1.11.0-cp36-cp36m-linux_aarch64.whl
RUN pip3 install onnxruntime_gpu-1.11.0-cp36-cp36m-linux_aarch64.whl

RUN pip3 install python-dotenv
RUN pip3 install tqdm
RUN pip3 install requests

COPY ./src/dl_images.py /usr/src/app/dl_images.py
