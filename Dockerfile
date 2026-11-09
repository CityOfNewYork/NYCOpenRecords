# syntax=docker/dockerfile:1
#
# OpenRecords application image (linux/amd64).
#   production (default)  gunicorn on :8080
#   development           flask run on :5000, plus test tools
# The same image runs Celery and one-off Flask commands by overriding the command.

# Multi-arch index digest for python:3.14.10-slim-trixie (Debian 13). The digest is what's
# pulled; when bumping, update tag and digest together.
ARG PYTHON_IMAGE=python:3.14.10-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f

# ================== BUILDER =================
FROM ${PYTHON_IMAGE} AS builder

# psycopg2 is built from source; everything else installs from wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/venv/bin:$PATH" \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv

COPY requirements/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# ================== RUNTIME BASE =================
FROM ${PYTHON_IMAGE} AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        # psycopg2
        libpq5 \
        # python-magic
        libmagic1 \
        # WeasyPrint letters; Liberation fonts are metric-compatible with Arial/Helvetica
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-liberation \
        # pdflatex for envelopes (hyphenat, seqsplit, wrapfig need -extra)
        texlive-latex-base texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 --user-group openrecords

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=openrecords.py

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
# Code stays root-owned (read-only to the app); only scratch directories are writable.
# Container storage is ephemeral: anything that must persist goes to Blob storage.
COPY . .
RUN mkdir -p logs quarantine/incoming quarantine/outgoing \
    && chown -R openrecords:openrecords logs quarantine

# ================== DEVELOPMENT =================
FROM runtime AS development

COPY requirements/dev.txt /tmp/dev.txt
RUN pip install --no-cache-dir -r /tmp/dev.txt

USER openrecords
EXPOSE 5000
# Runs migrations on start for local convenience only; production runs them as a separate one-off job.
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["flask", "run", "--host", "0.0.0.0"]

# ================== PRODUCTION (default) =================
FROM runtime AS production

# FLASK_CONFIG: without it the app falls back to DevelopmentConfig (DEBUG=True).
# FLASK_ENV: openrecords.py imports pytest (a dev-only package) unless this is "production".
ENV FLASK_CONFIG=production \
    FLASK_ENV=production

USER openrecords
EXPOSE 8080
CMD ["gunicorn", "-c", "python:gunicorn_config", "openrecords:app"]
