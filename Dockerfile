FROM python:3.14

RUN apt-get update &&\
    apt-get install -y tesseract-ocr &&\
    apt-get clean &&\
    rm -rf /var/lib/apt/lists/*

WORKDIR /
ADD requirements.txt .
RUN pip install -r requirements.txt
ADD scamdetect scamdetect
ADD bot.py .

VOLUME [ "/data" ]
WORKDIR /data

CMD ["python", "-u", "/bot.py"] 
