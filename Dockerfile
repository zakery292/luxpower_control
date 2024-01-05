FROM python:3.9-slim


ENV PYTHONUNBUFFERED=1
COPY . .
# Install required Python packages
RUN pip install --no-cache-dir numpy pandas scikit-learn paho-mqtt
# Make the start.sh script executable
RUN chmod a+x /start.sh

# Run the start.sh script when the container starts
CMD [ "/start.sh" ]
