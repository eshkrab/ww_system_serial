# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container to /app
WORKDIR /app

# Install system dependencies for USB serial
RUN apt-get update && apt-get install -y \
    usbutils 

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Define environment variable
ENV PYTHONUNBUFFERED=1

# Make ports available to the world outside this container
EXPOSE 5555 5568

# Run the command to start the player app
CMD [ "python", "app/app.py" ]

