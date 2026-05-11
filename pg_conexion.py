"""
pg_conexion.py
Módulo compartido de conexión a PostgreSQL.

Flujo:
  iPhone / Mac  →  actualizador.py (Railway)
                       → mensaje_api.py / exportador_api.py
                           → pg_conexion.py  ← estás aquí
                               → PostgreSQL (Railway)

Las URLs se leen desde variables de entorno configuradas en Railway.
En Railway: pestaña Variables → agregar DATABASE_URL_MIEMBROS y DATABASE_URL_CHAT
"""
import os
import psycopg2


def conectar_miembros():
    """Devuelve una conexión psycopg2 a club_miembros."""
    url = os.environ.get("DATABASE_URL_MIEMBROS")
    if not url:
        raise RuntimeError(
            "Variable de entorno DATABASE_URL_MIEMBROS no configurada.\n"
            "En Railway: pestaña Variables → agregar DATABASE_URL_MIEMBROS"
        )
    return psycopg2.connect(url)


def conectar_chat():
    """Devuelve una conexión psycopg2 a club_chat."""
    url = os.environ.get("DATABASE_URL_CHAT")
    if not url:
        raise RuntimeError(
            "Variable de entorno DATABASE_URL_CHAT no configurada.\n"
            "En Railway: pestaña Variables → agregar DATABASE_URL_CHAT"
        )
    return psycopg2.connect(url)
