FROM python:3.11.7-slim-bookworm

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

COPY ./requirements.txt .
RUN pip install -U pip
RUN pip install --no-cache-dir --no-deps -r requirements.txt

COPY . .
