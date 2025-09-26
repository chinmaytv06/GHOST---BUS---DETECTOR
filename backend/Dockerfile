FROM python:3.10-slim

WORKDIR /app

# Copy only requirements first
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the code
COPY . .

# Make start.sh executable
RUN chmod +x start.sh

EXPOSE 8000

# Use start.sh to run both uvicorn and ingester
CMD ["bash", "start.sh"]
