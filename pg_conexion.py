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

RECONEXIÓN AUTOMÁTICA:
El plan gratuito de Railway corta conexiones inactivas.
Esta implementación usa un pool simple que verifica si la conexión
sigue viva antes de usarla y reconecta automáticamente si no.
"""
import os
import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2 import OperationalError

# ── Pools globales ────────────────────────────────────────────
_pool_miembros = None
_pool_chat     = None


def _get_url_miembros():
    url = os.environ.get("DATABASE_URL_MIEMBROS")
    if not url:
        raise RuntimeError(
            "Variable de entorno DATABASE_URL_MIEMBROS no configurada.\n"
            "En Railway: pestaña Variables → agregar DATABASE_URL_MIEMBROS"
        )
    return url


def _get_url_chat():
    url = os.environ.get("DATABASE_URL_CHAT")
    if not url:
        raise RuntimeError(
            "Variable de entorno DATABASE_URL_CHAT no configurada.\n"
            "En Railway: pestaña Variables → agregar DATABASE_URL_CHAT"
        )
    return url


def _init_pool_miembros():
    global _pool_miembros
    _pool_miembros = pg_pool.SimpleConnectionPool(
        1, 4,
        _get_url_miembros(),
        connect_timeout=10,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5
    )


def _init_pool_chat():
    global _pool_chat
    _pool_chat = pg_pool.SimpleConnectionPool(
        1, 3,
        _get_url_chat(),
        connect_timeout=10,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5
    )


def _conn_viva(conn):
    """Verifica si una conexión sigue activa haciendo un ping liviano."""
    try:
        conn.cursor().execute("SELECT 1")
        return True
    except Exception:
        return False


def conectar_miembros():
    """
    Devuelve una conexión del pool a club_miembros.
    Si el pool no existe o la conexión está muerta, reconecta automáticamente.
    """
    global _pool_miembros
    try:
        if _pool_miembros is None:
            _init_pool_miembros()
        conn = _pool_miembros.getconn()
        if not _conn_viva(conn):
            # Conexión muerta — reiniciar el pool completo
            try:
                _pool_miembros.closeall()
            except Exception:
                pass
            _init_pool_miembros()
            conn = _pool_miembros.getconn()
        return conn
    except Exception:
        # Fallback: conexión directa sin pool
        return psycopg2.connect(
            _get_url_miembros(),
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5
        )


def liberar_miembros(conn):
    """Devuelve la conexión al pool de club_miembros."""
    global _pool_miembros
    try:
        if _pool_miembros:
            _pool_miembros.putconn(conn)
        else:
            conn.close()
    except Exception:
        pass


def conectar_chat():
    """
    Devuelve una conexión del pool a club_chat.
    Si el pool no existe o la conexión está muerta, reconecta automáticamente.
    """
    global _pool_chat
    try:
        if _pool_chat is None:
            _init_pool_chat()
        conn = _pool_chat.getconn()
        if not _conn_viva(conn):
            try:
                _pool_chat.closeall()
            except Exception:
                pass
            _init_pool_chat()
            conn = _pool_chat.getconn()
        return conn
    except Exception:
        # Fallback: conexión directa sin pool
        return psycopg2.connect(
            _get_url_chat(),
            connect_timeout=10,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5
        )


def liberar_chat(conn):
    """Devuelve la conexión al pool de club_chat."""
    global _pool_chat
    try:
        if _pool_chat:
            _pool_chat.putconn(conn)
        else:
            conn.close()
    except Exception:
        pass
