# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Python script into the container at /app
COPY tuya_exporter.py .

# Make port 9876 available (adjust if your EXPORTER_PORT is different)
EXPOSE 9876

# Run tuya_exporter.py when the container launches
CMD ["python", "./tuya_exporter.py"]