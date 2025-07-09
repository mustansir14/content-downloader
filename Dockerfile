# Use an official Python runtime as the base image
FROM python:3.10-alpine

# Set the working directory in the container
WORKDIR /app

# Install ffmpeg and other dependencies
RUN apk add --no-cache ffmpeg

COPY ./requirements.txt /app/requirements.txt

# Install any required dependencies
RUN pip install -r requirements.txt

# Copy your application code into the container
COPY . /app

CMD ["python", "main.py"]