# FROM localhost:5000/mypython:latest
FROM python:3.7


EXPOSE 8081

RUN apt-get update -y && \
    apt-get install -y python-pip python-dev && \
    apt-get install -y python-mysqldb zip

# We copy just the requirements.txt first to leverage Docker cache
RUN pip install -r requirements.txt

# Now we can cache our custom python3.7 image in docker hub for speed up
# please read README.md
