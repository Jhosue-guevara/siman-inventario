# Control de inventario — Almacenes Siman

Aplicacion web del inquilino `almacenes-siman` de la plataforma PaaS.
API REST y interfaz web sobre una base de datos PostgreSQL administrada.

## Stack

| Capa | Tecnologia |
|---|---|
| Lenguaje | Python 3.12 |
| Framework | Flask 3 |
| Servidor | Gunicorn |
| Acceso a datos | psycopg2 con consultas parametrizadas |
| Base de datos | PostgreSQL 16 |

## Variables de entorno

Ninguna credencial esta escrita en el codigo.

| Variable | Para que sirve |
|---|---|
| `DB_HOST` | Servidor de PostgreSQL |
| `DB_PORT` | Puerto, 5432 por omision |
| `DB_NAME` | Nombre de la base |
| `DB_USER` | Usuario |
| `DB_PASSWORD` | Contrasena |
| `SECRET_KEY` | Firma de las sesiones de Flask |

## API

| Metodo | Ruta | Que hace |
|---|---|---|
| GET | `/api/articulos` | Lista, admite `?q=` y `?departamento=` |
| GET | `/api/articulos/<id>` | Devuelve un articulo |
| POST | `/api/articulos` | Crea uno nuevo |
| PUT | `/api/articulos/<id>` | Actualiza |
| DELETE | `/api/articulos/<id>` | Elimina |
| GET | `/api/resumen` | Cifras del inventario |
| GET | `/salud` | Comprobacion de vida; 503 si la base no responde |

## Prueba local

```
pip install -r requirements.txt
cd app && python servidor.py
```

O con Docker:

```
docker build -t siman-python .
docker run -p 8000:8000 \
  -e DB_HOST=host.docker.internal -e DB_NAME=inventario \
  -e DB_USER=siman -e DB_PASSWORD=clave siman-python
```
