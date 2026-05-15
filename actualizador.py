"""
actualizador.py  —  PostgreSQL
Servidor Flask principal. Sirve INDEX.HTML al iPhone y orquesta
todas las rutas de la API (tareas, chat, badges).
"""
from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
import json
import os
import logging
import hashlib
from datetime import datetime, timedelta
from functools import wraps

try:
    import jwt as pyjwt
    JWT_OK = True
except ImportError:
    JWT_OK = False
    print("Aviso: PyJWT no instalado. Rutas /club/ no disponibles. Ejecutá: pip install PyJWT")

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
# JWT — autenticación del portal de clubs
# ─────────────────────────────────────────────────────────────
JWT_SECRET = os.environ.get("JWT_SECRET", "ika_blackbelt_club_secret_2024")
JWT_ALGO   = "HS256"
JWT_HORAS  = 8

def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(s), fmt).date()
        except Exception:
            continue
    return None

def _crear_token(club_id, nombre, cedula):
    payload = {
        "club_id": club_id,
        "nombre":  nombre,
        "cedula":  cedula,
        "exp":     datetime.utcnow() + timedelta(hours=JWT_HORAS)
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def _verificar_token(token):
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except Exception:
        return None

def require_club(f):
    """Decorador que valida el JWT y carga g.club_id, g.club_nombre, g.club_cedula."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not JWT_OK:
            return jsonify({"error": "PyJWT no instalado en el servidor"}), 503
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Token requerido"}), 401
        payload = _verificar_token(auth[7:])
        if not payload:
            return jsonify({"error": "Token inválido o expirado"}), 401
        g.club_id     = payload["club_id"]
        g.club_nombre = payload["nombre"]
        g.club_cedula = payload["cedula"]
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────
# MIGRACIÓN AUTOMÁTICA — se ejecuta en el primer request
# Crea todas las tablas de clubs si no existen
# ─────────────────────────────────────────────────────────────
_migrado = False

@app.before_request
def _antes_de_request():
    global _migrado
    if not _migrado:
        _migrar_tablas_club()
        _migrado = True

def _migrar_tablas_club():
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clubs (
                id                SERIAL        PRIMARY KEY,
                nombre            VARCHAR(200)  NOT NULL,
                ciudad            VARCHAR(100),
                estado            VARCHAR(20)   NOT NULL DEFAULT 'pendiente',
                fecha_solicitud   TIMESTAMP     NOT NULL DEFAULT NOW(),
                cedula_dueno      VARCHAR(20)   NOT NULL UNIQUE,
                nombres_dueno     VARCHAR(100)  NOT NULL,
                apellidos_dueno   VARCHAR(100)  NOT NULL,
                password_hash     VARCHAR(255)  NOT NULL DEFAULT '',
                debe_cambiar_pass BOOLEAN       NOT NULL DEFAULT TRUE
            )
        """)
        cur.execute("ALTER TABLE miembros ADD COLUMN IF NOT EXISTS ciudad_residencia VARCHAR(100)")
        cur.execute("ALTER TABLE miembros ADD COLUMN IF NOT EXISTS club_id INTEGER REFERENCES clubs(id) ON DELETE SET NULL")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categorias_club (
                id       SERIAL        PRIMARY KEY,
                club_id  INTEGER       NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
                nombre   VARCHAR(100)  NOT NULL,
                UNIQUE(club_id, nombre)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hist_plantillas (
                id     SERIAL        PRIMARY KEY,
                nombre VARCHAR(200)  NOT NULL,
                activa BOOLEAN       NOT NULL DEFAULT TRUE
            )
        """)
        cur.execute("ALTER TABLE hist_plantillas ADD COLUMN IF NOT EXISTS activa BOOLEAN NOT NULL DEFAULT TRUE")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hist_campos (
                id           SERIAL        PRIMARY KEY,
                plantilla_id INTEGER       NOT NULL REFERENCES hist_plantillas(id) ON DELETE CASCADE,
                orden        INTEGER       NOT NULL DEFAULT 0,
                etiqueta     VARCHAR(200)  NOT NULL,
                tipo         VARCHAR(50)   NOT NULL DEFAULT 'texto'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hist_registros (
                id           SERIAL  PRIMARY KEY,
                socio_id     INTEGER NOT NULL REFERENCES miembros(id)        ON DELETE CASCADE,
                plantilla_id INTEGER NOT NULL REFERENCES hist_plantillas(id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hist_valores (
                id          SERIAL  PRIMARY KEY,
                registro_id INTEGER NOT NULL REFERENCES hist_registros(id) ON DELETE CASCADE,
                campo_id    INTEGER NOT NULL REFERENCES hist_campos(id)    ON DELETE CASCADE,
                valor       TEXT
            )
        """)
        conn.commit()
        liberar_miembros(conn)
        print("[actualizador] ✅ Migración tablas club completada.")
    except Exception as e:
        print(f"[actualizador] ❌ Error en migración: {e}")


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


# ═════════════════════════════════════════════════════════════════════════════
# PORTAL DE CLUBS — rutas /club/...
# Autenticación via JWT. Cada club solo accede a sus propios datos.
# ═════════════════════════════════════════════════════════════════════════════

# ── SERVIR club.html ──────────────────────────────────────────────────────────
@app.route('/club')
@app.route('/club/')
def servir_club():
    return send_from_directory('.', 'club.html')


# ── REGISTRO (sin auth) ───────────────────────────────────────────────────────
@app.route('/club/registrar', methods=['POST'])
def club_registrar():
    d = request.get_json() or {}
    req = ["nombre", "ciudad", "cedula_dueno", "nombres_dueno", "apellidos_dueno", "password"]
    if not all((d.get(k) or "").strip() for k in req):
        return jsonify({"error": "Todos los campos son obligatorios"}), 400
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO clubs (nombre, ciudad, cedula_dueno, nombres_dueno,
                               apellidos_dueno, password_hash, debe_cambiar_pass, estado)
            VALUES (%s,%s,%s,%s,%s,%s,FALSE,'pendiente') RETURNING id
        """, (d["nombre"].strip(), d["ciudad"].strip(), d["cedula_dueno"].strip(),
              d["nombres_dueno"].strip(), d["apellidos_dueno"].strip(), _hash_pw(d["password"])))
        nuevo_id = cur.fetchone()[0]
        conn.commit()
        liberar_miembros(conn)
        return jsonify({"status": "ok", "id": nuevo_id,
                        "mensaje": "Solicitud enviada. El administrador de IKA Ecuador revisará y aprobará tu acceso en breve."})
    except Exception as e:
        if "unique" in str(e).lower():
            return jsonify({"error": "Ya existe un club registrado con esa cédula."}), 409
        return jsonify({"error": str(e)}), 500


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@app.route('/club/login', methods=['POST'])
def club_login():
    if not JWT_OK:
        return jsonify({"error": "PyJWT no instalado en el servidor"}), 503
    d      = request.get_json() or {}
    cedula = (d.get("cedula") or "").strip()
    pw     = (d.get("password") or "").strip()
    if not cedula or not pw:
        return jsonify({"error": "Cédula y contraseña requeridas"}), 400
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, nombre, estado, password_hash, debe_cambiar_pass
            FROM clubs WHERE cedula_dueno = %s
        """, (cedula,))
        row = cur.fetchone()
        liberar_miembros(conn)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    if not row:
        return jsonify({"error": "Cédula no registrada"}), 401
    club_id, nombre, estado, pw_hash, debe_cambiar = row
    if estado == 'pendiente':
        return jsonify({"error": "Tu solicitud está pendiente de aprobación por el administrador de IKA Ecuador."}), 403
    if estado == 'suspendido':
        return jsonify({"error": "Tu club ha sido suspendido. Contactá al administrador de IKA Ecuador."}), 403
    if _hash_pw(pw) != pw_hash:
        return jsonify({"error": "Contraseña incorrecta"}), 401
    token = _crear_token(club_id, nombre, cedula)
    return jsonify({"status": "ok", "token": token, "club_id": club_id,
                    "nombre": nombre, "debe_cambiar_pass": debe_cambiar})


# ── INFO DEL CLUB ─────────────────────────────────────────────────────────────
@app.route('/club/info', methods=['GET'])
@require_club
def club_info_get():
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, nombre, ciudad, estado, cedula_dueno,
                   nombres_dueno, apellidos_dueno, debe_cambiar_pass
            FROM clubs WHERE id = %s
        """, (g.club_id,))
        row = cur.fetchone()
        liberar_miembros(conn)
        if not row:
            return jsonify({"error": "Club no encontrado"}), 404
        return jsonify({"id": row[0], "nombre": row[1], "ciudad": row[2],
                        "estado": row[3], "cedula_dueno": row[4],
                        "nombres_dueno": row[5], "apellidos_dueno": row[6],
                        "debe_cambiar_pass": row[7]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/club/info', methods=['PUT'])
@require_club
def club_info_put():
    d      = request.get_json() or {}
    nombre = (d.get("nombre") or "").strip()
    ciudad = (d.get("ciudad") or "").strip()
    if not nombre:
        return jsonify({"error": "El nombre del club es obligatorio"}), 400
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("UPDATE clubs SET nombre=%s, ciudad=%s WHERE id=%s",
                    (nombre, ciudad, g.club_id))
        conn.commit()
        liberar_miembros(conn)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/club/password', methods=['PUT'])
@require_club
def club_password_put():
    d      = request.get_json() or {}
    actual = (d.get("actual") or "").strip()
    nueva  = (d.get("nueva")  or "").strip()
    if not actual or not nueva:
        return jsonify({"error": "Contraseña actual y nueva son requeridas"}), 400
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("SELECT password_hash FROM clubs WHERE id=%s", (g.club_id,))
        row = cur.fetchone()
        if not row or _hash_pw(actual) != row[0]:
            liberar_miembros(conn)
            return jsonify({"error": "Contraseña actual incorrecta"}), 401
        cur.execute("UPDATE clubs SET password_hash=%s, debe_cambiar_pass=FALSE WHERE id=%s",
                    (_hash_pw(nueva), g.club_id))
        conn.commit()
        liberar_miembros(conn)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── MIEMBROS DEL CLUB ─────────────────────────────────────────────────────────
_COLS_MIEMBRO = ["id","nombres","apellidos","cedula","categoria",
                 "ciudad_nacimiento","fecha_nacimiento","telefono",
                 "direccion","correo","fecha_ingreso","genero","ciudad_residencia"]

@app.route('/club/miembros', methods=['GET'])
@require_club
def club_miembros_get():
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, nombres, apellidos, cedula, categoria,
                   ciudad_nacimiento, TO_CHAR(fecha_nacimiento,'YYYY-MM-DD'),
                   telefono, direccion, correo,
                   TO_CHAR(fecha_ingreso,'YYYY-MM-DD'), genero, ciudad_residencia
            FROM miembros WHERE club_id=%s ORDER BY apellidos, nombres
        """, (g.club_id,))
        rows = [dict(zip(_COLS_MIEMBRO, r)) for r in cur.fetchall()]
        liberar_miembros(conn)
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/club/miembros', methods=['POST'])
@require_club
def club_miembros_post():
    d = request.get_json() or {}
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO miembros
                (nombres,apellidos,cedula,categoria,ciudad_nacimiento,fecha_nacimiento,
                 telefono,direccion,correo,fecha_ingreso,genero,ciudad_residencia,
                 password_hash,debe_cambiar_pass,club_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s) RETURNING id
        """, (d.get("nombres","").strip(), d.get("apellidos","").strip(),
              d.get("cedula","").strip(),   d.get("categoria","").strip(),
              d.get("ciudad_nacimiento","").strip(), _parse_date(d.get("fecha_nacimiento")),
              d.get("telefono","").strip(), d.get("direccion","").strip(),
              d.get("correo","").strip(),   _parse_date(d.get("fecha_ingreso")),
              d.get("genero","").strip(),   d.get("ciudad_residencia","").strip(),
              _hash_pw(d.get("cedula","")), g.club_id))
        nuevo_id = cur.fetchone()[0]
        conn.commit()
        liberar_miembros(conn)
        return jsonify({"status": "ok", "id": nuevo_id}), 201
    except Exception as e:
        if "unique" in str(e).lower():
            return jsonify({"error": "Ya existe un afiliado con esa cédula."}), 409
        return jsonify({"error": str(e)}), 500


@app.route('/club/miembros/<int:mid>', methods=['GET'])
@require_club
def club_miembro_get(mid):
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, nombres, apellidos, cedula, categoria,
                   ciudad_nacimiento, TO_CHAR(fecha_nacimiento,'YYYY-MM-DD'),
                   telefono, direccion, correo,
                   TO_CHAR(fecha_ingreso,'YYYY-MM-DD'), genero, ciudad_residencia
            FROM miembros WHERE id=%s AND club_id=%s
        """, (mid, g.club_id))
        row = cur.fetchone()
        liberar_miembros(conn)
        if not row:
            return jsonify({"error": "Miembro no encontrado"}), 404
        return jsonify(dict(zip(_COLS_MIEMBRO, row)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/club/miembros/<int:mid>', methods=['PUT'])
@require_club
def club_miembro_put(mid):
    d = request.get_json() or {}
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("SELECT id FROM miembros WHERE id=%s AND club_id=%s", (mid, g.club_id))
        if not cur.fetchone():
            liberar_miembros(conn)
            return jsonify({"error": "Miembro no encontrado"}), 404
        cur.execute("""
            UPDATE miembros SET
                nombres=%s, apellidos=%s, cedula=%s, categoria=%s,
                ciudad_nacimiento=%s, fecha_nacimiento=%s, telefono=%s,
                direccion=%s, correo=%s, fecha_ingreso=%s,
                genero=%s, ciudad_residencia=%s
            WHERE id=%s AND club_id=%s
        """, (d.get("nombres","").strip(), d.get("apellidos","").strip(),
              d.get("cedula","").strip(),   d.get("categoria","").strip(),
              d.get("ciudad_nacimiento","").strip(), _parse_date(d.get("fecha_nacimiento")),
              d.get("telefono","").strip(), d.get("direccion","").strip(),
              d.get("correo","").strip(),   _parse_date(d.get("fecha_ingreso")),
              d.get("genero","").strip(),   d.get("ciudad_residencia","").strip(),
              mid, g.club_id))
        conn.commit()
        liberar_miembros(conn)
        return jsonify({"status": "ok"})
    except Exception as e:
        if "unique" in str(e).lower():
            return jsonify({"error": "Ya existe un afiliado con esa cédula."}), 409
        return jsonify({"error": str(e)}), 500


@app.route('/club/miembros/<int:mid>', methods=['DELETE'])
@require_club
def club_miembro_delete(mid):
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("DELETE FROM miembros WHERE id=%s AND club_id=%s", (mid, g.club_id))
        if cur.rowcount == 0:
            liberar_miembros(conn)
            return jsonify({"error": "Miembro no encontrado"}), 404
        conn.commit()
        liberar_miembros(conn)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── BÚSQUEDA POR CÉDULA ───────────────────────────────────────────────────────
@app.route('/club/buscar', methods=['GET'])
@require_club
def club_buscar():
    cedula = (request.args.get("cedula") or "").strip()
    if not cedula:
        return jsonify({"error": "Cédula requerida"}), 400
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, nombres, apellidos, cedula, categoria,
                   ciudad_nacimiento, TO_CHAR(fecha_nacimiento,'YYYY-MM-DD'),
                   telefono, direccion, correo,
                   TO_CHAR(fecha_ingreso,'YYYY-MM-DD'), genero, ciudad_residencia
            FROM miembros WHERE cedula=%s AND club_id=%s
        """, (cedula, g.club_id))
        row = cur.fetchone()
        liberar_miembros(conn)
        if not row:
            return jsonify({"error": "No se encontró un afiliado con esa cédula en tu club"}), 404
        return jsonify(dict(zip(_COLS_MIEMBRO, row)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── CATEGORÍAS DEL CLUB ───────────────────────────────────────────────────────
@app.route('/club/categorias', methods=['GET'])
@require_club
def club_categorias_get():
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("SELECT id, nombre FROM categorias_club WHERE club_id=%s ORDER BY nombre",
                    (g.club_id,))
        rows = [{"id": r[0], "nombre": r[1]} for r in cur.fetchall()]
        liberar_miembros(conn)
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/club/categorias', methods=['POST'])
@require_club
def club_categorias_post():
    d      = request.get_json() or {}
    nombre = (d.get("nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "Nombre requerido"}), 400
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("INSERT INTO categorias_club (club_id, nombre) VALUES (%s,%s) RETURNING id",
                    (g.club_id, nombre))
        new_id = cur.fetchone()[0]
        conn.commit()
        liberar_miembros(conn)
        return jsonify({"status": "ok", "id": new_id}), 201
    except Exception as e:
        if "unique" in str(e).lower():
            return jsonify({"error": "Esa categoría ya existe."}), 409
        return jsonify({"error": str(e)}), 500


@app.route('/club/categorias/<int:cid>', methods=['DELETE'])
@require_club
def club_categorias_delete(cid):
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("DELETE FROM categorias_club WHERE id=%s AND club_id=%s", (cid, g.club_id))
        if cur.rowcount == 0:
            liberar_miembros(conn)
            return jsonify({"error": "Categoría no encontrada"}), 404
        conn.commit()
        liberar_miembros(conn)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── HISTORIAL ─────────────────────────────────────────────────────────────────
@app.route('/club/historial/plantillas', methods=['GET'])
@require_club
def club_hist_plantillas():
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""
            SELECT p.id, p.nombre, c.id, c.etiqueta, c.tipo, c.orden
            FROM hist_plantillas p
            JOIN hist_campos c ON c.plantilla_id = p.id
            WHERE p.activa = TRUE
            ORDER BY p.nombre, c.orden
        """)
        rows = cur.fetchall()
        liberar_miembros(conn)
        plantillas = {}
        for pid, pnom, cid, etq, tipo, orden in rows:
            if pid not in plantillas:
                plantillas[pid] = {"id": pid, "nombre": pnom, "campos": []}
            plantillas[pid]["campos"].append(
                {"id": cid, "etiqueta": etq, "tipo": tipo, "orden": orden})
        return jsonify(list(plantillas.values()))
    except Exception:
        return jsonify([])


@app.route('/club/historial/<int:socio_id>', methods=['GET'])
@require_club
def club_hist_get(socio_id):
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("SELECT id FROM miembros WHERE id=%s AND club_id=%s", (socio_id, g.club_id))
        if not cur.fetchone():
            liberar_miembros(conn)
            return jsonify({"error": "Miembro no encontrado"}), 404
        cur.execute("""
            SELECT r.id, p.nombre, c.etiqueta, v.valor, c.orden
            FROM hist_registros r
            JOIN hist_plantillas p ON p.id = r.plantilla_id
            JOIN hist_valores    v ON v.registro_id = r.id
            JOIN hist_campos     c ON c.id = v.campo_id
            WHERE r.socio_id = %s
            ORDER BY r.id DESC, c.orden
        """, (socio_id,))
        rows = cur.fetchall()
        liberar_miembros(conn)
        registros = {}
        for rid, plt_nom, etq, val, orden in rows:
            if rid not in registros:
                registros[rid] = {"id": rid, "plantilla": plt_nom, "valores": []}
            registros[rid]["valores"].append(
                {"etiqueta": etq, "valor": val or "", "orden": orden})
        for r in registros.values():
            r["valores"].sort(key=lambda x: x["orden"])
        return jsonify(list(registros.values()))
    except Exception:
        return jsonify([])


@app.route('/club/historial', methods=['POST'])
@require_club
def club_hist_post():
    d            = request.get_json() or {}
    socio_id     = d.get("socio_id")
    plantilla_id = d.get("plantilla_id")
    valores      = d.get("valores", {})
    if not socio_id or not plantilla_id:
        return jsonify({"error": "socio_id y plantilla_id requeridos"}), 400
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("SELECT id FROM miembros WHERE id=%s AND club_id=%s", (socio_id, g.club_id))
        if not cur.fetchone():
            liberar_miembros(conn)
            return jsonify({"error": "Miembro no encontrado"}), 404
        cur.execute("INSERT INTO hist_registros (socio_id, plantilla_id) VALUES (%s,%s) RETURNING id",
                    (socio_id, plantilla_id))
        reg_id = cur.fetchone()[0]
        for campo_id, valor in valores.items():
            cur.execute("INSERT INTO hist_valores (registro_id, campo_id, valor) VALUES (%s,%s,%s)",
                        (reg_id, int(campo_id), str(valor)))
        conn.commit()
        liberar_miembros(conn)
        return jsonify({"status": "ok", "id": reg_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/club/historial/<int:reg_id>', methods=['DELETE'])
@require_club
def club_hist_delete(reg_id):
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""
            DELETE FROM hist_registros WHERE id=%s
            AND socio_id IN (SELECT id FROM miembros WHERE club_id=%s)
        """, (reg_id, g.club_id))
        if cur.rowcount == 0:
            liberar_miembros(conn)
            return jsonify({"error": "Registro no encontrado"}), 404
        conn.commit()
        liberar_miembros(conn)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port)
