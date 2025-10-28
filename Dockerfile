FROM python:3.14

WORKDIR /
ADD requirements.txt .
RUN pip install -r requirements.txt
ADD bot.py .

VOLUME [ "/data" ]
WORKDIR /data

CMD ["python", "-u", "/bot.py"] 
