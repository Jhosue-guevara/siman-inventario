# Aplicacion del inquilino Almacenes Siman: Python con Flask sobre PostgreSQL.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /srv/

# Gunicorn sirve la aplicacion; Flask solo se usa en pruebas locales.
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", \
     "--timeout", "30", "--access-logfile", "-", "servidor:app"]
