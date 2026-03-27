# Use a lightweight Python base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the honeypot server code into the container
COPY server.py .
COPY __init__.py .

# Assuming the honeypot server might have dependencies,
# for example, to interact with an LLM or Kafka.
# If you have a requirements.txt in the honeypot directory, uncomment the next two lines.
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# The command to run the honeypot server
# Replace 'server.py' if your entrypoint script has a different name
CMD ["python", "server.py"]
