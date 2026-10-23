"""
Aplicacion del inquilino Almacenes Siman.

Expone dos caras sobre la misma base de datos:
  - una API REST en /api/articulos
  - una interfaz web en / que la consume

Se ejecuta con Gunicorn en produccion; Flask solo en pruebas locales.
"""

import os
import re
from decimal import Decimal, InvalidOperation

from flask import Flask, jsonify, request, render_template, redirect, url_for, flash

import basedatos as bd

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave-de-pruebas")

SKU = re.compile(r"^[A-Za-z0-9\-]{2,32}$")


# ------------------------------------------------------------ validacion
def validar(d):
    errores = []

    sku = (d.get("sku") or "").strip()
    if not sku:
        errores.append("El SKU es obligatorio.")
    elif not SKU.match(sku):
        errores.append("El SKU solo admite letras, numeros y guiones.")

    if not (d.get("nombre") or "").strip():
        errores.append("El nombre del articulo es obligatorio.")
    if not (d.get("departamento") or "").strip():
        errores.append("El departamento es obligatorio.")

    try:
        precio = Decimal(str(d.get("precio", "")).strip())
        if precio < 0:
            errores.append("El precio no puede ser negativo.")
    except (InvalidOperation, ValueError):
        errores.append("El precio debe ser un numero.")

    try:
        existencias = int(str(d.get("existencias", "")).strip())
        if existencias < 0:
            errores.append("Las existencias no pueden ser negativas.")
    except ValueError:
        errores.append("Las existencias deben ser un numero entero.")

    return errores


def limpiar(d):
    return {
        "sku": (d.get("sku") or "").strip().upper(),
        "nombre": (d.get("nombre") or "").strip(),
        "departamento": (d.get("departamento") or "").strip(),
        "precio": str(d.get("precio", "0")).strip(),
        "existencias": int(str(d.get("existencias", "0")).strip()),
    }


def serializar(fila):
    if not fila:
        return None
    salida = dict(fila)
    if salida.get("precio") is not None:
        salida["precio"] = float(salida["precio"])
    if salida.get("creado"):
        salida["creado"] = salida["creado"].isoformat()
    return salida


# ------------------------------------------------------------ API REST
@app.get("/api/articulos")
def api_listar():
    datos = bd.listar(request.args.get("q", ""), request.args.get("departamento", ""))
    return jsonify({"total": len(datos), "articulos": [serializar(x) for x in datos]})


@app.get("/api/articulos/<int:id_articulo>")
def api_obtener(id_articulo):
    fila = bd.obtener(id_articulo)
    if not fila:
        return jsonify({"error": "El articulo no existe."}), 404
    return jsonify(serializar(fila))


@app.post("/api/articulos")
def api_crear():
    cuerpo = request.get_json(silent=True) or {}
    errores = validar(cuerpo)
    if errores:
        return jsonify({"errores": errores}), 400
    try:
        return jsonify(serializar(bd.crear(limpiar(cuerpo)))), 201
    except Exception as err:
        return jsonify({"error": f"No se pudo crear: {err}"}), 409


@app.put("/api/articulos/<int:id_articulo>")
def api_actualizar(id_articulo):
    cuerpo = request.get_json(silent=True) or {}
    errores = validar(cuerpo)
    if errores:
        return jsonify({"errores": errores}), 400
    fila = bd.actualizar(id_articulo, limpiar(cuerpo))
    if not fila:
        return jsonify({"error": "El articulo no existe."}), 404
    return jsonify(serializar(fila))


@app.delete("/api/articulos/<int:id_articulo>")
def api_eliminar(id_articulo):
    if not bd.eliminar(id_articulo):
        return jsonify({"error": "El articulo no existe."}), 404
    return "", 204


@app.get("/api/resumen")
def api_resumen():
    r = dict(bd.resumen())
    r["valor"] = float(r["valor"])
    return jsonify(r)


@app.get("/salud")
def salud():
    """Comprobacion de vida: responde 503 si la base no contesta."""
    try:
        bd.resumen()
        return jsonify({"estado": "ok", "base_de_datos": "conectada"})
    except Exception as err:
        return jsonify({"estado": "degradado", "detalle": str(err)}), 503


# ------------------------------------------------------------ interfaz web
@app.get("/")
def inicio():
    busqueda = request.args.get("q", "").strip()
    depto = request.args.get("departamento", "").strip()
    editar = request.args.get("editar", type=int)

    contexto = {
        "busqueda": busqueda,
        "departamento_filtro": depto,
        "estado_bd": "conectada",
        "articulos": [],
        "cifras": {"articulos": 0, "departamentos": 0, "unidades": 0, "valor": 0},
        "departamentos": [],
        "editando": None,
        "version_pg": "",
    }

    try:
        contexto["articulos"] = bd.listar(busqueda, depto)
        contexto["cifras"] = bd.resumen()
        contexto["departamentos"] = bd.departamentos()
        contexto["version_pg"] = bd.version_motor()
        if editar:
            contexto["editando"] = bd.obtener(editar)
    except Exception as err:
        contexto["estado_bd"] = "sin conexion"
        flash(f"No se pudo consultar la base de datos: {err}", "error")

    return render_template("inicio.html", **contexto)


@app.post("/guardar")
def guardar():
    id_articulo = request.form.get("id", type=int)
    errores = validar(request.form)

    if errores:
        for x in errores:
            flash(x, "error")
        return redirect(url_for("inicio", editar=id_articulo or None))

    try:
        if id_articulo:
            bd.actualizar(id_articulo, limpiar(request.form))
            flash("Los cambios quedaron guardados.", "ok")
        else:
            bd.crear(limpiar(request.form))
            flash("Articulo agregado al inventario.", "ok")
    except Exception as err:
        texto = str(err)
        if "unique" in texto.lower() or "duplicate" in texto.lower():
            flash("Ya existe un articulo con ese SKU.", "error")
        else:
            flash(f"No se pudo guardar: {err}", "error")

    return redirect(url_for("inicio"))


@app.post("/eliminar/<int:id_articulo>")
def quitar(id_articulo):
    try:
        bd.eliminar(id_articulo)
        flash("El articulo fue retirado del inventario.", "ok")
    except Exception as err:
        flash(f"No se pudo eliminar: {err}", "error")
    return redirect(url_for("inicio"))


# ------------------------------------------------------------ arranque
def iniciar():
    try:
        bd.preparar_esquema()
        app.logger.info("Esquema de la base de datos listo")
    except Exception as err:
        app.logger.warning("No se pudo preparar el esquema: %s", err)


iniciar()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=False)
