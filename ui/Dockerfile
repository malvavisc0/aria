FROM node:23-alpine AS prisma
RUN npm install -g prisma@latest
RUN prisma --version
ENTRYPOINT ["prisma"]
FROM python:3.12-slim AS webui
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt update
RUN pip install --upgrade pip
RUN apt install -y libjpeg-dev zlib1g-dev libxml2-dev libxslt-dev libpng-dev
RUN apt install -y ffmpeg curl
COPY ./requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN playwright install-deps
RUN playwright install
RUN mkdir /code
ENV PYTHONPATH="${PYTHONPATH}:/code/"
WORKDIR /code
RUN chainlit init
EXPOSE 9000
ENTRYPOINT ["chainlit", "run", "app.py", "--watch", "--headless", "--debug", "--host", "0.0.0.0", "--port", "9000"]