FROM python:3.11.9-slim-bookworm

RUN apt-get update && apt-get -y install libmagic-dev libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
COPY requirements/requirements.txt ./requirements/
RUN pip install -r requirements/requirements.txt

COPY app app ./app/
COPY migrations ./migrations/
COPY config.py openrecords.py ./

COPY entrypoint.sh ./
RUN chmod +x ./entrypoint.sh

EXPOSE 5000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["flask", "run", "--host", "0.0.0.0"]
