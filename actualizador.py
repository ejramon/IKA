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

from pg_conexion import conectar_miembros, liberar_miembros

try:
    import jwt as pyjwt
    JWT_OK = True
except ImportError:
    JWT_OK = False
    print("Aviso: PyJWT no instalado. Rutas /club/ no disponibles. Ejecutá: pip install PyJWT")

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
        # Nuevos campos en clubs
        cur.execute("ALTER TABLE clubs ADD COLUMN IF NOT EXISTS direccion VARCHAR(200)")
        cur.execute("ALTER TABLE clubs ADD COLUMN IF NOT EXISTS telefono  VARCHAR(20)")
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
        # Tablas de programas (inscriptos y asistencias del club)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS programa_inscriptos (
                id          SERIAL  PRIMARY KEY,
                programa_id INTEGER NOT NULL REFERENCES programas(id)  ON DELETE CASCADE,
                club_id     INTEGER NOT NULL REFERENCES clubs(id)      ON DELETE CASCADE,
                socio_id    INTEGER NOT NULL REFERENCES miembros(id)   ON DELETE CASCADE,
                UNIQUE(programa_id, club_id, socio_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS programa_asistencias (
                id          SERIAL  PRIMARY KEY,
                sesion_id   INTEGER NOT NULL REFERENCES programa_sesiones(id) ON DELETE CASCADE,
                socio_id    INTEGER NOT NULL REFERENCES miembros(id)          ON DELETE CASCADE,
                club_id     INTEGER NOT NULL REFERENCES clubs(id)             ON DELETE CASCADE,
                asistio     BOOLEAN         DEFAULT NULL,
                UNIQUE(sesion_id, socio_id, club_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS programa_comentarios (
                id          SERIAL      PRIMARY KEY,
                programa_id INTEGER     NOT NULL REFERENCES programas(id)  ON DELETE CASCADE,
                club_id     INTEGER     NOT NULL REFERENCES clubs(id)      ON DELETE CASCADE,
                socio_id    INTEGER     NOT NULL REFERENCES miembros(id)   ON DELETE CASCADE,
                autor       VARCHAR(10) NOT NULL DEFAULT 'club',
                texto       TEXT        NOT NULL,
                creado_en   TIMESTAMP   NOT NULL DEFAULT NOW()
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
    generar_json_para_safari()
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
# RUTA 7: OBTENER CONVERSACIONES CON ADMINS
# ─────────────────────────────────────────────────────────────
@app.route('/obtener_conversaciones_admin', methods=['GET'])
def api_obtener_conversaciones_admin():
    try:
        evento_id = int(request.args.get('evento'))
        socio_id  = int(request.args.get('socio'))
        from pg_conexion import conectar_chat
        conn_chat = conectar_chat()
        cur = conn_chat.cursor()
        cur.execute("""
            SELECT c.participante_a
            FROM conversaciones c
            WHERE c.evento_id = %s
              AND c.tipo_conv = 'individual'
              AND c.participante_b = %s
        """, (evento_id, socio_id))
        admin_ids = [row[0] for row in cur.fetchall()]
        conn_chat.close()
        if not admin_ids:
            return jsonify([])
        conn_m = conectar_miembros()
        cur_m = conn_m.cursor()
        cur_m.execute("""
            SELECT id, nombres || ' ' || apellidos AS nombre
            FROM miembros WHERE id = ANY(%s)
        """, (admin_ids,))
        nombres = {row[0]: row[1] for row in cur_m.fetchall()}
        liberar_miembros(conn_m)
        result = []
        for aid in admin_ids:
            result.append({
                "admin_id":     aid,
                "admin_nombre": nombres.get(aid, "Administrador")
            })
        return jsonify(result)
    except Exception as e:
        print(f"[obtener_conversaciones_admin] Error: {e}")
        return jsonify([])


# ═════════════════════════════════════════════════════════════════════════════
# PORTAL DE CLUBS — rutas /club/...
# Autenticación via JWT. Cada club solo accede a sus propios datos.
# ═════════════════════════════════════════════════════════════════════════════

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
                   nombres_dueno, apellidos_dueno, debe_cambiar_pass,
                   COALESCE(direccion,''), COALESCE(telefono,'')
            FROM clubs WHERE id = %s
        """, (g.club_id,))
        row = cur.fetchone()
        liberar_miembros(conn)
        if not row:
            return jsonify({"error": "Club no encontrado"}), 404
        return jsonify({"id": row[0], "nombre": row[1], "ciudad": row[2],
                        "estado": row[3], "cedula_dueno": row[4],
                        "nombres_dueno": row[5], "apellidos_dueno": row[6],
                        "debe_cambiar_pass": row[7],
                        "direccion": row[8], "telefono": row[9]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/club/info', methods=['PUT'])
@require_club
def club_info_put():
    d        = request.get_json() or {}
    nombre   = (d.get("nombre")   or "").strip()
    ciudad   = (d.get("ciudad")   or "").strip()
    direccion= (d.get("direccion")or "").strip()
    telefono = (d.get("telefono") or "").strip()
    if not nombre:
        return jsonify({"error": "El nombre del club es obligatorio"}), 400
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("UPDATE clubs SET nombre=%s, ciudad=%s, direccion=%s, telefono=%s WHERE id=%s",
                    (nombre, ciudad, direccion, telefono, g.club_id))
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
        if not row:
            liberar_miembros(conn)
            return jsonify({"error": "Miembro no encontrado"}), 404
        data = dict(zip(_COLS_MIEMBRO, row))
        # Subcategorías dinámicas desde programas activos
        cur.execute("""
            SELECT DISTINCT p.subcategoria
            FROM programa_inscriptos pi
            JOIN programas p ON p.id = pi.programa_id
            WHERE pi.socio_id = %s AND pi.club_id = %s
              AND p.subcategoria IS NOT NULL AND p.subcategoria != ''
              AND p.estado = 'activo'
            ORDER BY p.subcategoria
        """, (mid, g.club_id))
        data["subcategorias"] = [r[0] for r in cur.fetchall()]
        liberar_miembros(conn)
        return jsonify(data)
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
        # Categorías propias del club
        cur.execute("SELECT id, nombre FROM categorias_club WHERE club_id=%s ORDER BY nombre",
                    (g.club_id,))
        propias = [{"id": f"c_{r[0]}", "nombre": r[1], "fuente": "club", "id_real": r[0]}
                   for r in cur.fetchall()]
        # Categorías globales de BlackBelt (tabla categorias)
        cur.execute("SELECT id, nombre FROM categorias ORDER BY nombre")
        globales = [{"id": f"g_{r[0]}", "nombre": r[1], "fuente": "global", "id_real": r[0]}
                    for r in cur.fetchall()]
        liberar_miembros(conn)
        # Unir: globales primero, luego propias; sin duplicar nombres
        nombres_globales = {c["nombre"].lower() for c in globales}
        propias_unicas   = [c for c in propias if c["nombre"].lower() not in nombres_globales]
        return jsonify(globales + propias_unicas)
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
        # Verificar si ya existe en categorías globales
        cur.execute("SELECT id FROM categorias WHERE LOWER(nombre)=LOWER(%s)", (nombre,))
        if cur.fetchone():
            liberar_miembros(conn)
            return jsonify({"error": f"La categoría \"{nombre}\" ya existe en las categorías globales de IKA Ecuador."}), 409
        # Verificar si ya existe en categorías del club
        cur.execute("SELECT id FROM categorias_club WHERE club_id=%s AND LOWER(nombre)=LOWER(%s)",
                    (g.club_id, nombre))
        if cur.fetchone():
            liberar_miembros(conn)
            return jsonify({"error": f"La categoría \"{nombre}\" ya está registrada en tu club."}), 409
        cur.execute("INSERT INTO categorias_club (club_id, nombre) VALUES (%s,%s) RETURNING id",
                    (g.club_id, nombre))
        new_id = cur.fetchone()[0]
        conn.commit()
        liberar_miembros(conn)
        return jsonify({"status": "ok", "id": new_id}), 201
    except Exception as e:
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


@app.route('/club/importar_excel', methods=['POST'])
@require_club
def club_importar_excel():
    """
    Recibe un JSON con array 'miembros' (filas del Excel ya parseadas en el cliente).
    Inserta los que no existan (por cédula). Devuelve resumen.
    """
    d       = request.get_json() or {}
    filas   = d.get("miembros", [])
    if not filas:
        return jsonify({"error": "No se recibieron datos"}), 400
    ok_count  = 0
    dup_count = 0
    err_count = 0
    errores   = []
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        for idx, f in enumerate(filas, 1):
            try:
                cedula = str(f.get("cedula") or "").strip()
                if not cedula:
                    err_count += 1
                    errores.append(f"Fila {idx}: cédula vacía")
                    continue
                # Verificar duplicado global
                cur.execute("SELECT id FROM miembros WHERE cedula=%s", (cedula,))
                if cur.fetchone():
                    dup_count += 1
                    continue
                cur.execute("""
                    INSERT INTO miembros
                        (nombres,apellidos,cedula,categoria,ciudad_nacimiento,fecha_nacimiento,
                         telefono,direccion,correo,fecha_ingreso,genero,ciudad_residencia,
                         password_hash,debe_cambiar_pass,club_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s)
                """, (
                    str(f.get("nombres","")).strip(),
                    str(f.get("apellidos","")).strip(),
                    cedula,
                    str(f.get("categoria","")).strip(),
                    str(f.get("ciudad_nacimiento","")).strip(),
                    _parse_date(f.get("fecha_nacimiento")),
                    str(f.get("telefono","")).strip(),
                    str(f.get("direccion","")).strip(),
                    str(f.get("correo","")).strip(),
                    _parse_date(f.get("fecha_ingreso")),
                    str(f.get("genero","")).strip(),
                    str(f.get("ciudad_residencia","")).strip(),
                    _hash_pw(cedula),
                    g.club_id
                ))
                ok_count += 1
            except Exception as e:
                err_count += 1
                errores.append(f"Fila {idx}: {str(e)[:80]}")
        conn.commit()
        liberar_miembros(conn)
        return jsonify({
            "status":    "ok",
            "importados": ok_count,
            "duplicados": dup_count,
            "errores":    err_count,
            "detalle_errores": errores[:20]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═════════════════════════════════════════════════════════════════════════════
# PROGRAMAS DEL CLUB
# ═════════════════════════════════════════════════════════════════════════════

# ── Listar programas asignados al club ────────────────────────────────────────
@app.route('/club/programas', methods=['GET'])
@require_club
def club_programas_get():
    """
    Devuelve los programas que BlackBelt desplegó para este club,
    junto con si ya fueron configurados (tienen inscriptos).
    """
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""
            SELECT p.id, p.nombre,
                   TO_CHAR(p.fecha_inicio, 'YYYY-MM-DD'),
                   TO_CHAR(p.fecha_fin,    'YYYY-MM-DD'),
                   p.dias_semana, p.horas_diarias, p.estado,
                   p.descripcion, p.subcategoria,
                   (SELECT COUNT(*) FROM programa_inscriptos pi
                    WHERE pi.programa_id = p.id AND pi.club_id = %s) AS n_inscriptos,
                   (SELECT COUNT(*) FROM programa_sesiones ps
                    WHERE ps.programa_id = p.id) AS n_sesiones
            FROM programas p
            JOIN programa_clubs pc ON pc.programa_id = p.id
            WHERE pc.club_id = %s
            ORDER BY p.fecha_inicio DESC
        """, (g.club_id, g.club_id))
        rows = cur.fetchall()
        liberar_miembros(conn)

        _DIAS = {1:"Lun",2:"Mar",3:"Mié",4:"Jue",5:"Vie",6:"Sáb",7:"Dom"}
        result = []
        for row in rows:
            dias_str = row[4] or ""
            try:
                dias_fmt = ", ".join(
                    _DIAS[int(d)] for d in dias_str.split(",") if d.strip()
                )
            except Exception:
                dias_fmt = dias_str
            result.append({
                "id":           row[0],
                "nombre":       row[1],
                "fecha_inicio": row[2],
                "fecha_fin":    row[3],
                "dias_semana":  dias_str,
                "dias_fmt":     dias_fmt,
                "horas":        float(row[5]) if row[5] else 0,
                "estado":       row[6],
                "descripcion":  row[7] or "",
                "subcategoria": row[8] or "",
                "n_inscriptos": row[9],
                "n_sesiones":   row[10],
                "configurado":  row[9] > 0,
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Obtener sesiones de un programa ──────────────────────────────────────────
@app.route('/club/programas/<int:prog_id>/sesiones', methods=['GET'])
@require_club
def club_prog_sesiones(prog_id):
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        # Verificar que el programa pertenece al club
        cur.execute("""SELECT 1 FROM programa_clubs
                       WHERE programa_id=%s AND club_id=%s""", (prog_id, g.club_id))
        if not cur.fetchone():
            liberar_miembros(conn)
            return jsonify({"error": "Programa no encontrado"}), 404
        cur.execute("""
            SELECT id, TO_CHAR(fecha, 'YYYY-MM-DD'), TO_CHAR(fecha, 'DD/MM/YYYY')
            FROM programa_sesiones
            WHERE programa_id = %s
            ORDER BY fecha
        """, (prog_id,))
        rows = cur.fetchall()
        liberar_miembros(conn)
        return jsonify([{"id": r[0], "fecha": r[1], "fecha_fmt": r[2]} for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Obtener / guardar inscriptos del programa ─────────────────────────────────
@app.route('/club/programas/<int:prog_id>/inscriptos', methods=['GET'])
@require_club
def club_prog_inscriptos_get(prog_id):
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""SELECT 1 FROM programa_clubs
                       WHERE programa_id=%s AND club_id=%s""", (prog_id, g.club_id))
        if not cur.fetchone():
            liberar_miembros(conn)
            return jsonify({"error": "Programa no encontrado"}), 404
        cur.execute("""
            SELECT pi.socio_id, m.nombres, m.apellidos, m.cedula, m.categoria
            FROM programa_inscriptos pi
            JOIN miembros m ON m.id = pi.socio_id
            WHERE pi.programa_id = %s AND pi.club_id = %s
            ORDER BY m.apellidos, m.nombres
        """, (prog_id, g.club_id))
        rows = cur.fetchall()
        liberar_miembros(conn)
        return jsonify([{
            "socio_id": r[0], "nombres": r[1], "apellidos": r[2],
            "cedula": r[3], "categoria": r[4]
        } for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/club/programas/<int:prog_id>/inscriptos', methods=['POST'])
@require_club
def club_prog_inscriptos_post(prog_id):
    """Guarda/reemplaza los inscriptos de un programa para este club."""
    d        = request.get_json() or {}
    socio_ids = d.get("socio_ids", [])
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""SELECT 1 FROM programa_clubs
                       WHERE programa_id=%s AND club_id=%s""", (prog_id, g.club_id))
        if not cur.fetchone():
            liberar_miembros(conn)
            return jsonify({"error": "Programa no encontrado"}), 404
        # Reemplazar inscriptos
        cur.execute("""DELETE FROM programa_inscriptos
                       WHERE programa_id=%s AND club_id=%s""", (prog_id, g.club_id))
        for sid in socio_ids:
            cur.execute("""
                INSERT INTO programa_inscriptos (programa_id, club_id, socio_id)
                VALUES (%s, %s, %s) ON CONFLICT DO NOTHING
            """, (prog_id, g.club_id, int(sid)))
        conn.commit()
        liberar_miembros(conn)
        return jsonify({"status": "ok", "inscriptos": len(socio_ids)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Asistencias por sesión ────────────────────────────────────────────────────
@app.route('/club/programas/sesion/<int:sesion_id>/asistencias', methods=['GET'])
@require_club
def club_asistencias_get(sesion_id):
    """
    Devuelve la asistencia de los inscriptos del club para una sesión.
    Si no hay registro todavía, devuelve los inscriptos con asistio=null (sin registro).
    """
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""
            SELECT ps.programa_id FROM programa_sesiones ps
            JOIN programa_clubs pc ON pc.programa_id = ps.programa_id
            WHERE ps.id = %s AND pc.club_id = %s
        """, (sesion_id, g.club_id))
        row = cur.fetchone()
        if not row:
            liberar_miembros(conn)
            return jsonify({"error": "Sesión no encontrada"}), 404
        prog_id = row[0]

        cur.execute("""
            SELECT pi.socio_id, m.nombres, m.apellidos, m.categoria,
                   pa.asistio
            FROM programa_inscriptos pi
            JOIN miembros m ON m.id = pi.socio_id
            LEFT JOIN programa_asistencias pa
                ON pa.sesion_id = %s AND pa.socio_id = pi.socio_id AND pa.club_id = %s
            WHERE pi.programa_id = %s AND pi.club_id = %s
            ORDER BY m.apellidos, m.nombres
        """, (sesion_id, g.club_id, prog_id, g.club_id))
        rows = cur.fetchall()
        liberar_miembros(conn)
        return jsonify([{
            "socio_id": r[0], "nombres": r[1], "apellidos": r[2],
            "categoria": r[3], "asistio": r[4]  # None → null en JSON
        } for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/club/programas/sesion/<int:sesion_id>/asistencias', methods=['POST'])
@require_club
def club_asistencias_post(sesion_id):
    """
    Guarda/actualiza la asistencia de todos los alumnos de una sesión.
    Body: { asistencias: [{socio_id: N, asistio: true/false}, ...] }
    """
    d = request.get_json() or {}
    asistencias = d.get("asistencias", [])
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        # Verificar que la sesión pertenece al club
        cur.execute("""
            SELECT ps.programa_id FROM programa_sesiones ps
            JOIN programa_clubs pc ON pc.programa_id = ps.programa_id
            WHERE ps.id = %s AND pc.club_id = %s
        """, (sesion_id, g.club_id))
        if not cur.fetchone():
            liberar_miembros(conn)
            return jsonify({"error": "Sesión no encontrada"}), 404

        for item in asistencias:
            socio_id = int(item["socio_id"])
            asistio_raw = item.get("asistio")  # puede ser True, False, o None
            if asistio_raw is None:
                # Sin registro — eliminar fila si existe
                cur.execute("""
                    DELETE FROM programa_asistencias
                    WHERE sesion_id = %s AND socio_id = %s AND club_id = %s
                """, (sesion_id, socio_id, g.club_id))
            else:
                asistio = bool(asistio_raw)
                cur.execute("""
                    INSERT INTO programa_asistencias (sesion_id, socio_id, club_id, asistio)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (sesion_id, socio_id, club_id)
                    DO UPDATE SET asistio = EXCLUDED.asistio
                """, (sesion_id, socio_id, g.club_id, asistio))
        conn.commit()
        liberar_miembros(conn)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# ── Comentarios por alumno en un programa ────────────────────────────────────
@app.route('/club/programas/<int:prog_id>/comentarios/<int:socio_id>', methods=['GET'])
@require_club
def club_comentarios_get(prog_id, socio_id):
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""
            SELECT pc.autor, pc.texto,
                   TO_CHAR(pc.creado_en, 'DD/MM/YYYY HH24:MI'),
                   COALESCE(c.nombre, 'Admin IKA')
            FROM programa_comentarios pc
            LEFT JOIN clubs c ON c.id = pc.club_id
            WHERE pc.programa_id=%s AND pc.club_id=%s AND pc.socio_id=%s
            ORDER BY pc.creado_en ASC
        """, (prog_id, g.club_id, socio_id))
        rows = cur.fetchall()
        liberar_miembros(conn)
        return jsonify([{
            "autor": r[0], "texto": r[1],
            "fecha": r[2], "nombre_autor": r[3]
        } for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/club/programas/<int:prog_id>/comentarios/<int:socio_id>', methods=['POST'])
@require_club
def club_comentarios_post(prog_id, socio_id):
    d     = request.get_json() or {}
    texto = (d.get("texto") or "").strip()
    if not texto:
        return jsonify({"error": "Texto vacío"}), 400
    try:
        conn = conectar_miembros()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO programa_comentarios
                (programa_id, club_id, socio_id, autor, texto)
            VALUES (%s, %s, %s, 'club', %s)
        """, (prog_id, g.club_id, socio_id, texto))
        conn.commit()
        liberar_miembros(conn)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────
# INICIO DEL SERVIDOR
# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port)
