FROM python:3.9-slim

WORKDIR /usr/src/app
ENV PYTHONUNBUFFERED=1

# Install required Python packages
RUN pip install --no-cache-dir numpy pandas scikit-learn paho-mqtt

# Copy your Python scripts and the start.sh script into the container
COPY soc_collections.py predict_soc.py init_db.py start.sh /usr/src/app/

# Make the start.sh script executable
RUN chmod a+x start.sh

# Run the start.sh script when the container starts
CMD ["./start.sh"]