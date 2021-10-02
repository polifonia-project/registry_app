# FROM web_base
FROM python:latest

WORKDIR /app

COPY requirements.txt requirements.txt
# COPY ./docker_base/wait-for-it.sh wait-for-it.sh 

RUN pip install -r requirements.txt

COPY ./wait-for-it.sh /wait-for-it.sh 

# create the app user
RUN addgroup --system app && adduser --system --group app

ENV APP_HOME /app
RUN chown -R app:app $APP_HOME
RUN ["chmod", "+x", "/wait-for-it.sh"]

# change to the app user
USER app

# CMD ["/bin/bash"] 
# if you want to debug something

# CMD ["/wait-for-it.sh", "db:8080", "--", "python", "app.py","80"]