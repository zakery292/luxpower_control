FROM python:3.9
# Set the working directory
WORKDIR /opt/

# Install jq and other required packages
RUN apk add --no-cache jq

# Install required Python packages
RUN pip install --no-cache-dir numpy pandas scikit-learn paho-mqtt

# Copy your scripts to the container
COPY soc_collections.py predict_soc.py init_db.py run.sh ./

# Make the run.sh script executable
RUN chmod a+x /opt/run.sh

# Run the run.sh script when the container starts
CMD [ "/opt/run.sh" ]