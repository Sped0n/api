FROM python:3.9.16-slim-bullseye

MAINTAINER sped0n

RUN mkdir /site && chmod 777 /site

WORKDIR /site

#RUN apt -qq update && apt -qq install -y python3 python3-pip

COPY . .

EXPOSE 8080

RUN pip3 install -r requirements.txt

CMD ["bash","bash.sh"]
