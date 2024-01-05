FROM python:3.9-slim

WORKDIR /usr/src/app
ENV PYTHONUNBUFFERED=1
COPY . .

RUN pip install --no-cache-dir numpy pandas scikit-learn paho-mqtt

# Run the initialization script first
CMD ["python", "./init_db.py"]

# Then run your main script that starts both Python scripts
CMD ["python", "./main.py"]