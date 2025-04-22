FROM node:23-slim AS prisma
RUN npm install -g prisma@latest
RUN prisma --version
ENTRYPOINT ["prisma"]
FROM python:3.13-slim AS webui
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt update
RUN apt install -y make build-essential libjpeg-dev zlib1g-dev libxml2-dev libxslt-dev libpng-dev ffmpeg curl
COPY ./requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt
RUN playwright install-deps
RUN playwright install
RUN mkdir /code
ENV PYTHONPATH="/code"
WORKDIR /code
RUN chainlit init
EXPOSE 9000
ENTRYPOINT ["chainlit", "run", "webui.py", "--watch", "--headless", "--host", "0.0.0.0", "--port", "9000"]