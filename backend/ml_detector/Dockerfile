# Use a lightweight Python base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the detector script into the container
COPY live_detector.py .

# Install necessary Python libraries
# scapy: for packet sniffing
# requests: to call the API server
RUN pip install --no-cache-dir scapy requests

# This is the command that will run when the container starts.
# The script is now configured via environment variables set in docker-compose.yml
CMD ["python", "live_detector.py"]
