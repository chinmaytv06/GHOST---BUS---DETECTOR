FROM python:3.10-slim

WORKDIR /app

# Copy only requirements first
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the code
COPY . .

EXPOSE 8000

# Because main.py is inside backend/app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
