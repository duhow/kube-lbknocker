FROM python:3.12-slim

COPY . /app
RUN useradd app && \
    pip3 install --no-cache -r /app/requirements.txt

USER app
ENTRYPOINT ["python3", "/app/main.py"]
