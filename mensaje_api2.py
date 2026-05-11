"""
mensaje_api.py  —  PostgreSQL
Maneja toda la lógica de mensajería del chat (club_chat).
Usado por: actualizador.py
"""
import os
from datetime import datetime
from pg_conexion import conectar_chat


# ─────────────────────────────────────────────────────────────
# OBTENER MENSAJES DE UNA SALA
# ─────────────────────────────────────────────────────────────
def obtener_mensajes_sala(evento_id, socio_id, target_id):
    conn = conectar_chat()
    cursor = conn.cursor()
    try:
        if target_id == 'GENERAL':
            query = """
                SELECT m.remitente_nombre, m.texto,
                       TO_CHAR(m.timestamp, 'YYYY-MM-DD HH24:MI:SS') AS timestamp
                FROM mensajes m
                JOIN conversaciones c ON m.conversacion_id = c.id
                WHERE m.evento_id = %s
                  AND c.tipo_conv = 'grupal'
                  AND NOT m.borrado
                ORDER BY m.timestamp ASC
            """
            cursor.execute(query, (evento_id,))
        else:
            query = """
                SELECT m.remitente_nombre, m.texto,
                       TO_CHAR(m.timestamp, 'YYYY-MM-DD HH24:MI:SS') AS timestamp
                FROM mensajes m
                JOIN conversaciones c ON m.conversacion_id = c.id
                WHERE m.evento_id = %s
                  AND c.tipo_conv = 'individual'
                  AND ((c.participante_a = %s AND c.participante_b = %s)
                       OR (c.participante_a = %s AND c.participante_b = %s))
                  AND NOT m.borrado
                ORDER BY m.timestamp ASC
            """
            cursor.execute(query, (evento_id, socio_id, target_id, target_id, socio_id))

        columnas = [col[0] for col in cursor.description]
        return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]

    except Exception as e:
        print(f"Error recuperando mensajes: {e}")
        return []
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# REGISTRAR UN NUEVO MENSAJE
# ─────────────────────────────────────────────────────────────
def registrar_nuevo_mensaje(datos):
    conn = conectar_chat()
    cursor = conn.cursor()
    try:
        evento_id        = datos['evento_id']
        remitente_nombre = datos['remitente_nombre']
        socio_id         = datos['remitente_id']
        target_id        = datos.get('receptor_id')
        texto            = datos['texto']

        conversacion_id = None
        destinatario_id = None

        if target_id == 'GENERAL':
            cursor.execute(
                "SELECT id FROM conversaciones WHERE evento_id = %s AND tipo_conv = 'grupal'",
                (evento_id,)
            )
            row = cursor.fetchone()
            if row:
                conversacion_id = row[0]
            else:
                cursor.execute(
                    """INSERT INTO conversaciones
                           (evento_id, nombre_conv, tipo_conv, participante_a)
                       VALUES (%s, 'Chat Grupal', 'grupal', %s)
                       RETURNING id""",
                    (evento_id, socio_id)
                )
                conversacion_id = cursor.fetchone()[0]
        else:
            destinatario_id = int(target_id)
            cursor.execute(
                """SELECT id FROM conversaciones
                   WHERE evento_id = %s AND tipo_conv = 'individual'
                     AND ((participante_a = %s AND participante_b = %s)
                          OR (participante_a = %s AND participante_b = %s))""",
                (evento_id, socio_id, target_id, target_id, socio_id)
            )
            row = cursor.fetchone()
            if row:
                conversacion_id = row[0]
            else:
                cursor.execute(
                    """INSERT INTO conversaciones
                           (evento_id, nombre_conv, tipo_conv, participante_a, participante_b)
                       VALUES (%s, 'Privado', 'individual', %s, %s)
                       RETURNING id""",
                    (evento_id, socio_id, target_id)
                )
                conversacion_id = cursor.fetchone()[0]

        # PG tiene DEFAULT NOW() en timestamp, leido y borrado DEFAULT FALSE
        cursor.execute(
            """INSERT INTO mensajes
                   (conversacion_id, evento_id, remitente_nombre,
                    destinatario_id, texto, leido, borrado)
               VALUES (%s, %s, %s, %s, %s, FALSE, FALSE)""",
            (conversacion_id, evento_id, remitente_nombre, destinatario_id, texto)
        )
        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        print(f"Error crítico en BD al registrar mensaje: {e}")
        return False
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# MARCAR MENSAJES COMO LEÍDOS
# ─────────────────────────────────────────────────────────────
def marcar_leido(evento_id, socio_id, target_id):
    """Marca leídos los mensajes privados o registra visita al grupal."""
    conn = conectar_chat()
    cursor = conn.cursor()
    try:
        if target_id == 'GENERAL':
            cursor.execute(
                "SELECT id FROM conversaciones WHERE evento_id = %s AND tipo_conv = 'grupal'",
                (evento_id,)
            )
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    """INSERT INTO ultima_lectura (socio_id, conversacion_id, visto_en)
                       VALUES (%s, %s, NOW())
                       ON CONFLICT (socio_id, conversacion_id)
                       DO UPDATE SET visto_en = NOW()""",
                    (socio_id, row[0])
                )
        else:
            cursor.execute(
                """UPDATE mensajes SET leido = TRUE
                   WHERE evento_id = %s
                     AND destinatario_id = %s
                     AND NOT leido
                     AND conversacion_id IN (
                         SELECT id FROM conversaciones
                         WHERE tipo_conv = 'individual'
                           AND ((participante_a = %s AND participante_b = %s)
                                OR (participante_a = %s AND participante_b = %s))
                     )""",
                (evento_id, socio_id, socio_id, int(target_id), int(target_id), socio_id)
            )
        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        print(f"Error marcando como leído: {e}")
        return False
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────
# OBTENER MENSAJES NO LEÍDOS
# ─────────────────────────────────────────────────────────────
def obtener_no_leidos(evento_id, socio_id):
    """Devuelve { total, detalle } con mensajes sin leer por conversación."""
    conn = conectar_chat()
    cursor = conn.cursor()
    detalle = {}
    total   = 0
    try:
        # ── GRUPAL: hay algo nuevo desde la última visita? ──
        cursor.execute(
            "SELECT id FROM conversaciones WHERE evento_id = %s AND tipo_conv = 'grupal'",
            (evento_id,)
        )
        row = cursor.fetchone()
        if row:
            conv_id_grupal = row[0]
            cursor.execute(
                "SELECT visto_en FROM ultima_lectura WHERE socio_id = %s AND conversacion_id = %s",
                (socio_id, conv_id_grupal)
            )
            lectura = cursor.fetchone()
            if lectura:
                cursor.execute(
                    """SELECT COUNT(*) FROM mensajes
                       WHERE conversacion_id = %s
                         AND timestamp > %s
                         AND NOT borrado""",
                    (conv_id_grupal, lectura[0])
                )
            else:
                cursor.execute(
                    "SELECT COUNT(*) FROM mensajes WHERE conversacion_id = %s AND NOT borrado",
                    (conv_id_grupal,)
                )
            if cursor.fetchone()[0] > 0:
                detalle['GENERAL'] = 1
                total += 1

        # ── INDIVIDUALES: mensajes dirigidos a mí sin leer ──
        cursor.execute(
            """SELECT c.participante_a, c.participante_b, COUNT(m.id)
               FROM conversaciones c
               JOIN mensajes m ON m.conversacion_id = c.id
               WHERE c.evento_id = %s
                 AND c.tipo_conv = 'individual'
                 AND (c.participante_a = %s OR c.participante_b = %s)
                 AND m.destinatario_id = %s
                 AND NOT m.leido
                 AND NOT m.borrado
               GROUP BY c.id, c.participante_a, c.participante_b""",
            (evento_id, socio_id, socio_id, socio_id)
        )
        for part_a, part_b, count in cursor.fetchall():
            otro = part_b if part_a == socio_id else part_a
            if otro is not None and count > 0:
                detalle[str(otro)] = count
                total += count

        return {'total': total, 'detalle': detalle}

    except Exception as e:
        print(f"Error obteniendo no leídos: {e}")
        return {'total': 0, 'detalle': {}}
    finally:
        conn.close()
