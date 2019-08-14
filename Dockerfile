# if you decide cache you docker image
# replace this line
FROM python:3.7


EXPOSE 1234

RUN apt-get update -y && \
    apt-get install -y python-pip python-dev && \
    apt-get install -y python-mysqldb zip

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /project/requirements.txt

WORKDIR ./project

RUN pip install -r requirements.txt

COPY . /project

# ENTRYPOINT [ "python" ]
# CMD python manage.py db upgrade ; \
#    python initial_data.py ; \ 
#    flask run --host=0.0.0.0 --port=8081
