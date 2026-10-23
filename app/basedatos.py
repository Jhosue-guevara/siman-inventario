"""
Acceso a PostgreSQL.

Las credenciales llegan siempre por variables de entorno: no hay ninguna
cadena de conexion en el codigo, de modo que el repositorio puede ser
publico sin exponer nada.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager


def parametros():
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
        "dbname": os.environ.get("DB_NAME", "inventario"),
        "user": os.environ.get("DB_USER", "siman"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "connect_timeout": 5,
    }


@contextmanager
def conexion():
    """Abre y cierra la conexion, confirmando o deshaciendo la transaccion."""
    cnx = psycopg2.connect(**parametros())
    try:
        yield cnx
        cnx.commit()
    except Exception:
        cnx.rollback()
        raise
    finally:
        cnx.close()


@contextmanager
def cursor():
    with conexion() as cnx:
        with cnx.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur


def preparar_esquema():
    """Crea la tabla y carga datos de ejemplo en el primer arranque."""
    with cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS articulos (
                id          SERIAL PRIMARY KEY,
                sku         VARCHAR(32)  NOT NULL UNIQUE,
                nombre      VARCHAR(140) NOT NULL,
                departamento VARCHAR(60) NOT NULL,
                precio      NUMERIC(10,2) NOT NULL DEFAULT 0,
                existencias INTEGER NOT NULL DEFAULT 0,
                creado      TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("SELECT COUNT(*) AS n FROM articulos")
        if cur.fetchone()["n"] == 0:
            cur.executemany(
                """INSERT INTO articulos (sku, nombre, departamento, precio, existencias)
                   VALUES (%s, %s, %s, %s, %s)""",
                [
                    ("HOG-1001", "Juego de sabanas matrimonial", "Hogar", 34.90, 42),
                    ("HOG-1002", "Set de ollas de acero, 5 piezas", "Hogar", 89.00, 18),
                    ("ELE-2001", "Televisor LED 43 pulgadas", "Electronica", 289.00, 12),
                    ("ELE-2002", "Audifonos inalambricos", "Electronica", 45.50, 60),
                    ("ROP-3001", "Camisa de vestir, manga larga", "Ropa", 24.90, 85),
                    ("ROP-3002", "Pantalon de mezclilla", "Ropa", 32.00, 74),
                    ("JUG-4001", "Rompecabezas 1000 piezas", "Jugueteria", 12.75, 30),
                    ("DEP-5001", "Mancuernas ajustables, par", "Deportes", 68.00, 15),
                ],
            )


def listar(busqueda="", departamento=""):
    sql = "SELECT * FROM articulos WHERE TRUE"
    args = []
    if busqueda:
        sql += " AND (nombre ILIKE %s OR sku ILIKE %s)"
        args += [f"%{busqueda}%", f"%{busqueda}%"]
    if departamento:
        sql += " AND departamento = %s"
        args.append(departamento)
    sql += " ORDER BY departamento, nombre"
    with cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()


def obtener(id_articulo):
    with cursor() as cur:
        cur.execute("SELECT * FROM articulos WHERE id = %s", (id_articulo,))
        return cur.fetchone()


def crear(d):
    with cursor() as cur:
        cur.execute(
            """INSERT INTO articulos (sku, nombre, departamento, precio, existencias)
               VALUES (%(sku)s, %(nombre)s, %(departamento)s, %(precio)s, %(existencias)s)
               RETURNING *""",
            d,
        )
        return cur.fetchone()


def actualizar(id_articulo, d):
    datos = dict(d, id=id_articulo)
    with cursor() as cur:
        cur.execute(
            """UPDATE articulos
               SET sku = %(sku)s, nombre = %(nombre)s, departamento = %(departamento)s,
                   precio = %(precio)s, existencias = %(existencias)s
               WHERE id = %(id)s
               RETURNING *""",
            datos,
        )
        return cur.fetchone()


def eliminar(id_articulo):
    with cursor() as cur:
        cur.execute("DELETE FROM articulos WHERE id = %s RETURNING id", (id_articulo,))
        return cur.fetchone() is not None


def resumen():
    with cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS articulos,
                   COUNT(DISTINCT departamento) AS departamentos,
                   COALESCE(SUM(existencias), 0) AS unidades,
                   COALESCE(SUM(precio * existencias), 0) AS valor
            FROM articulos
        """)
        return cur.fetchone()


def departamentos():
    with cursor() as cur:
        cur.execute("SELECT DISTINCT departamento FROM articulos ORDER BY departamento")
        return [f["departamento"] for f in cur.fetchall()]


def version_motor():
    with cursor() as cur:
        cur.execute("SHOW server_version")
        return cur.fetchone()["server_version"]
