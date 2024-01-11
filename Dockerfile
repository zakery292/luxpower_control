FROM python:3.9

WORKDIR /opt/

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir numpy pandas scikit-learn paho-mqtt APScheduler python-dateutil flask

COPY soc_collections.py predict_soc.py init_db.py db_cleanup.py solar_collections.py run.sh ./
# Copy the templates directory
COPY templates/ /opt/templates/
# Copy the new web application files
COPY app.py templates/ /opt/

RUN chmod a+x /opt/run.sh

CMD [ "/opt/run.sh" ]