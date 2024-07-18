# ================== PRODUCTION =================
FROM python:3.11.9-slim-bookworm AS production

RUN apt-get update \
    && apt-get -y install libmagic-dev \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
    libpq-dev gcc
COPY requirements/prod.txt ./requirements/
RUN pip install -r requirements/prod.txt
RUN pip install gunicorn

COPY app ./app/
COPY migrations ./migrations/
COPY config.py openrecords.py gunicorn_config.py ./

COPY entrypoint.sh ./
RUN chmod +x ./entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "-c", "python:gunicorn_config", "openrecords:app"]

# ================== DEVELOPMENT =================
FROM python:3.11.9-slim-bookworm AS development

RUN apt-get update && apt-get -y install libmagic-dev libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
COPY requirements/dev.txt ./requirements/
RUN pip install -r requirements/dev.txt

COPY app app ./app/
COPY migrations ./migrations/
COPY config.py openrecords.py ./

COPY entrypoint.sh ./
RUN chmod +x ./entrypoint.sh

EXPOSE 5000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["flask", "run", "--host", "0.0.0.0"]
