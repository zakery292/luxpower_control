FROM python:3.9-slim

WORKDIR /opt/
ENV PYTHONUNBUFFERED=1
COPY soc_collections.py predict_soc.py init_db.py run.sh ./
# Install required Python packages
RUN pip install --no-cache-dir numpy pandas scikit-learn paho-mqtt
# Make the start.sh script executable
RUN chmod a+x /opt/run.sh

# Run the start.sh script when the container starts
CMD [ "/opt/run.sh" ]
