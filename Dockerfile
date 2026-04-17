FROM python:3.12-slim

WORKDIR /app

# Install system dependencies required for dev environment
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to cache it
COPY requirements.txt requirements_dev.txt requirements_test.txt ./

# Upgrade pip and install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r requirements_dev.txt && \
    pip install -r requirements_test.txt

# Do not copy project files here, we will mount them via docker-compose
# Keep the container running for dev usage
CMD ["tail", "-f", "/dev/null"]
