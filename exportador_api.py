"""
exportador_api.py  —  PostgreSQL
Genera data_servidor.json leyendo club_miembros en Railway.
Lo llama actualizador.py cada vez que el iPhone actualiza una tarea.
"""
import json
import os
from pg_conexion import conectar_miembros, liberar_miembros


def generar_json_para_safari():
    try:
        conn = conectar_miembros()
    except Exception as e:
        print(f"[exportador_api] Error conectando a PostgreSQL: {e}")
        return

    cursor = conn.cursor()
    try:
        # ── Consulta principal54 ──────────────────────────────────────────
        # Las fechas vienen como objetos date de PG → las formateamos con
        # TO_CHAR para que el JSON sea siempre un string "DD/MM/YYYY"
        query = """
        SELECT
            m.cedula,
            m.nombres || ' ' || m.apellidos     AS nombre_completo,
            m.id                                AS socio_id,
            e.id                                AS evento_id,
            e.nombre                            AS evento_nombre,
            TO_CHAR(e.fecha, 'DD/MM/YYYY')      AS evento_fecha,
            j.rol                               AS miembro_rol,
            j.coordinador_id,
            r.id                                AS resp_id,
            r.descripcion                       AS resp_desc,
            r.estado                            AS resp_estado
        FROM miembros m
        JOIN jerarquia_roles j  ON m.id       = j.socio_id
        JOIN eventos e          ON j.evento_id = e.id
        LEFT JOIN responsabilidades r
               ON (e.id = r.evento_id AND m.id = r.socio_id)
        ORDER BY m.cedula, e.id, r.id
        """
        cursor.execute(query)
        filas = cursor.fetchall()

        data_sintetica = {}

        for fila in filas:
            (cedula, nombre_completo, socio_id,
             ev_id, ev_nombre, ev_fecha,
             rol, sup_id,
             r_id, r_desc, r_estado) = fila

            if cedula not in data_sintetica:
                data_sintetica[cedula] = {
                    "nombre":   nombre_completo,
                    "socio_id": socio_id,
                    "eventos":  {}
                }

            ev_key = str(ev_id)
            if ev_key not in data_sintetica[cedula]["eventos"]:
                data_sintetica[cedula]["eventos"][ev_key] = {
                    "titulo":            ev_nombre,
                    "fecha":             ev_fecha or "",
                    "rol":               rol,
                    "superior_id":       sup_id,
                    "responsabilidades": {}
                }

            if r_id is not None:
                # ── Checklist items de esta responsabilidad ──
                # completado es BOOLEAN en PG → lo convertimos a 0/1
                # para que el iPhone lo maneje igual que antes
                cursor.execute(
                    """SELECT texto,
                              CASE WHEN completado THEN 1 ELSE 0 END AS esta_listo,
                              id
                       FROM checklist_items
                       WHERE responsabilidad_id = %s
                       ORDER BY id""",
                    (r_id,)
                )
                items = cursor.fetchall()

                lista_items = []
                for it in items:
                    lista_items.append({
                        "tarea_texto": it[0],
                        "esta_listo":  it[1],   # 0 o 1 — mismo formato que SQLite
                        "id_tarea":    it[2]    # el iPhone lo usa como llave
                    })

                resp_key = str(r_id)
                data_sintetica[cedula]["eventos"][ev_key]["responsabilidades"][resp_key] = {
                    "titulo_resp":    r_desc,
                    "estado_resp":    r_estado,
                    "items_checklist": lista_items
                }

        # ── Guardar JSON ────────────────────────────────────────────────
        output_path = os.path.join(os.path.dirname(__file__), 'data_servidor.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_sintetica, f, indent=4, ensure_ascii=False)

        print(f"[exportador_api] data_servidor.json actualizado — {len(data_sintetica)} miembros.")

    except Exception as e:
        print(f"[exportador_api] Error técnico: {e}")
    finally:
        liberar_miembros(conn)


if __name__ == "__main__":
    generar_json_para_safari()
