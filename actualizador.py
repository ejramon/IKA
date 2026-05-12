"""
actualizador.py  —  PostgreSQL
Servidor Flask principal. Sirve INDEX.HTML al iPhone y orquesta
todas las rutas de la API (tareas, chat, badges).
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import logging
from datetime import datetime

from pg_conexion import conectar_miembros, liberar_miembros

try:
    from exportador_api import generar_json_para_safari
except ImportError:
    def generar_json_para_safari():
        print("Aviso: No se pudo importar exportador_api.py.")

try:
    from mensaje_api import (registrar_nuevo_mensaje, obtener_mensajes_sala,
                             marcar_leido, obtener_no_leidos)
except ImportError:
    print("Error: No se encontró mensaje_api.py. El chat no funcionará.")

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

LOG_FILE = 'registro_actividad.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(message)s')


# ─────────────────────────────────────────────────────────────
# HELPER: ejecutar escritura en club_miembros
# ─────────────────────────────────────────────────────────────
def ejecutar_db(query, params):
    """Ejecuta un query de escritura en club_miembros y hace commit."""
    try:
        conn = conectar_miembros()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        liberar_miembros(conn)
        return True
    except Exception as e:
        print(f"Error de base de datos: {e}")
        return False


# ─────────────────────────────────────────────────────────────
# RUTA 0: SERVIR data_servidor.json — siempre fresco, sin caché
# ─────────────────────────────────────────────────────────────
@app.route('/data_servidor.json')
def servir_data():
    generar_json_para_safari()   # regenera desde PostgreSQL antes de servir
    try:
        with open('data_servidor.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        response = jsonify(data)
    except Exception:
        response = jsonify({})
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma']        = 'no-cache'
    return response


# ─────────────────────────────────────────────────────────────
# SERVIR INDEX.HTML
# ─────────────────────────────────────────────────────────────
@app.route('/')
def servir_index():
    return send_from_directory('.', 'INDEX.HTML')


# ─────────────────────────────────────────────────────────────
# RUTA 1: ACTUALIZACIÓN DE TAREAS
# ─────────────────────────────────────────────────────────────
@app.route('/actualizar_tareas', methods=['POST'])
def actualizar_tareas():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No se recibieron datos"}), 400

    socio_id = data.get('socio_id')
    cambios  = data.get('cambios')

    if not socio_id or not cambios:
        return jsonify({"status": "error", "message": "Datos incompletos"}), 400

    exitos = 0
    for id_tarea, nuevo_estado in cambios.items():
        # nuevo_estado viene como 0/1 desde el iPhone → convertir a BOOLEAN de PG
        estado_bool = bool(int(nuevo_estado))
        query = "UPDATE checklist_items SET completado = %s WHERE id = %s"
        if ejecutar_db(query, (estado_bool, id_tarea)):
            exitos += 1
            logging.info(f"Socio ID {socio_id} - Tarea ID {id_tarea} - Estado: {nuevo_estado}")

    if exitos > 0:
        generar_json_para_safari()

    return jsonify({
        "status":      "success",
        "mensaje":     f"Procesado: {exitos} éxitos.",
        "actualizado": datetime.now().strftime("%H:%M:%S")
    })


# ─────────────────────────────────────────────────────────────
# RUTA 2: ENVIAR MENSAJE
# ─────────────────────────────────────────────────────────────
@app.route('/enviar_mensaje', methods=['POST'])
def api_enviar_mensaje():
    datos = request.get_json()
    exito = registrar_nuevo_mensaje(datos)
    if exito:
        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"status": "error"}), 500


# ─────────────────────────────────────────────────────────────
# RUTA 3: OBTENER MENSAJES
# ─────────────────────────────────────────────────────────────
@app.route('/obtener_chat', methods=['GET'])
def api_obtener_chat():
    evento = request.args.get('evento')
    socio  = request.args.get('socio')
    target = request.args.get('target')
    mensajes = obtener_mensajes_sala(evento, socio, target)
    return jsonify(mensajes)


# ─────────────────────────────────────────────────────────────
# RUTA 4: MARCAR LEÍDO
# ─────────────────────────────────────────────────────────────
@app.route('/marcar_leido', methods=['POST'])
def api_marcar_leido():
    datos     = request.get_json()
    evento_id = datos.get('evento_id')
    socio_id  = datos.get('socio_id')
    target_id = datos.get('target_id')
    exito = marcar_leido(evento_id, socio_id, target_id)
    if exito:
        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"status": "error"}), 500


# ─────────────────────────────────────────────────────────────
# RUTA 5: OBTENER NO LEÍDOS
# ─────────────────────────────────────────────────────────────
@app.route('/obtener_no_leidos', methods=['GET'])
def api_obtener_no_leidos():
    evento_id = request.args.get('evento')
    socio_id  = int(request.args.get('socio'))
    resultado = obtener_no_leidos(evento_id, socio_id)
    return jsonify(resultado)


# ─────────────────────────────────────────────────────────────
# RUTA 6: OBTENER NOMBRE DE UN SOCIO POR ID
# ─────────────────────────────────────────────────────────────
@app.route('/obtener_nombre_socio', methods=['GET'])
def api_obtener_nombre_socio():
    try:
        socio_id = int(request.args.get('socio_id'))
        conn = conectar_miembros()
        cur = conn.cursor()
        cur.execute("SELECT nombres, apellidos FROM miembros WHERE id = %s", (socio_id,))
        row = cur.fetchone()
        liberar_miembros(conn)
        if row:
            return jsonify({"nombre": f"{row[0]} {row[1]}".strip()})
        return jsonify({"nombre": "Administrador"})
    except Exception:
        return jsonify({"nombre": "Administrador"})


# ─────────────────────────────────────────────────────────────
# INICIO DEL SERVIDOR
# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port)
