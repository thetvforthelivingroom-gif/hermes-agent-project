# Use lightweight Python Alpine base image
FROM python:3.12-alpine

# Set working directory
WORKDIR /app

# Copy application source code
COPY . /app

# Install system build dependencies (needed for some Python packages)
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

# Install Python dependencies
RUN pip install --no-cache-dir requests beautifulsoup4 python-dotenv openai

# Expose default server port (if using api_server default 8080)
EXPOSE 8080

# Default command runs the API server
CMD ["python", "api_server.py"]
