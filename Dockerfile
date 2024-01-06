FROM python:3.9

WORKDIR /opt/

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir numpy pandas scikit-learn paho-mqtt APScheduler python-dateutil

COPY soc_collections.py predict_soc.py init_db.py db_cleanup.py run.sh ./

RUN chmod a+x /opt/run.sh

CMD [ "/opt/run.sh" ]