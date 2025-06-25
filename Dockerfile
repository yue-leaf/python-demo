FROM python:3.12-slim
RUN apt-get update && apt-get install -y gcc
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "main.py"]