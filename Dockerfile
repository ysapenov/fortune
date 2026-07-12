FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium
# Copy the source code
COPY . .

# Expose the application port
EXPOSE 8000

# Start the application
CMD ["python", "run.py"]
