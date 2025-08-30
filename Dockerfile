# Python 3.10.11 slim image use करो
FROM python:3.10.11-slim

# Working directory set करो
WORKDIR /app

# System dependencies install करो
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt copy करो और install करो
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# बाकी code copy करो
COPY . .

# Run करो Extractor module
CMD ["python", "-m", "Extractor"]
