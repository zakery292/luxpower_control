# Use Home Assistant base image for ARMv7
ARG BUILD_FROM=homeassistant/armv7-base:latest
FROM $BUILD_FROM

# Set the working directory
WORKDIR /opt/

# Install Python and required packages
RUN apk add --no-cache python3 py3-pip \
    && pip install --no-cache-dir numpy pandas scikit-learn paho-mqtt

# Copy your scripts to the container
COPY soc_collections.py predict_soc.py init_db.py run.sh ./

# Make the run.sh script executable
RUN chmod a+x /opt/run.sh

# Run the run.sh script when the container starts
CMD [ "/opt/run.sh" ]