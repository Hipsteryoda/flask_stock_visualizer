FROM python:3.11.4

COPY . /app
WORKDIR /app
 
RUN pip install -r requirements.txt
EXPOSE 5000
 
CMD ["python3", "app.py"]