FROM python:3.9

MAINTAINER sped0n

RUN mkdir /site && chmod 777 /site

WORKDIR /site

COPY . .

EXPOSE 8080

RUN pip3 install -r requirements.txt

CMD ["bash","bash.sh"]
