# Use an official Python runtime as a parent image
FROM python:3.12-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies, ADB tools, and tzdata for timezone management
RUN apt-get update && apt-get install -y android-tools-adb tzdata && \
    pip install --no-cache-dir -r requirements.txt

# Set timezone environment variable
ENV TZ=Asia/Kolkata

# Link timezone file to ensure correct time zone is used inside the container
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

EXPOSE 8123

# Set up PATH for ADB
ENV PATH=$PATH:/usr/bin/

# Run adbserver.py directly using CMD
CMD ["python3", "adbserver.py"]