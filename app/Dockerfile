FROM python:3.9

RUN mkdir /app
WORKDIR /app
ADD . /app/
RUN pip install -r requirements.txt

EXPOSE 5000
CMD ["python", "/app/main.py"]

# ENV FLASK_APP main.py
# CMD flask run --host=0.0.0.0 --port=5000