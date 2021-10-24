FROM python:3.9

RUN mkdir /app
WORKDIR /app
ADD . /app/

RUN python3 -m venv /opt/venv
RUN . /opt/venv/bin/activate && pip install -r requirements.txt

EXPOSE 5000
CMD . /opt/venv/bin/activate && exec python /app/main.py
