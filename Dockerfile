FROM python:3.12.9
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r requirements.txt
COPY src/ .
RUN python manage.py collectstatic --noinput
