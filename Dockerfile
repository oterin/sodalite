FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY ./server_requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./server /code/server

EXPOSE 10000

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "10000"]
