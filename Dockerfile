# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.8-slim-buster


EXPOSE 80

# Run this when "flask run" is called
ENV FLASK_APP=elsdan_server.py

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Nextcloud authentication + token
ENV NEXTCLOUD_AUTH_URL='https://nextcloud.elsdan.com/apps/oauth2/authorize'
ENV NEXTCLOUD_TOKEN_URL='https://nextcloud.elsdan.com/apps/oauth2/api/v1/token'
ENV ENV_DIRECTORY='.env'

ENV MYSQL_USER=${MYSQL_USER}
ENV MYSQL_PASSWORD=${MYSQL_PASSWORD}
ENV MYSQL_DATABASE=${MYSQL_DATABASE}
ENV DB_HOST=${DB_HOST}

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app
COPY . /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["gunicorn", "-t", "3600", "--bind", "0.0.0.0:80", "app:app"]
