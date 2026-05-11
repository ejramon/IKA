-- ============================================================
--  BLACKBELT CLUB -- Schema PostgreSQL
--  BASE DE DATOS: club_chat
--  Migrado desde: club_chat.db
--  Generado: 2026-05-10
--
--  MEJORAS SOBRE SQLITE:
--    [1] ENUM para tipo de conversación
--    [2] Fechas como TIMESTAMP real (no TEXT)
--    [3] NOTIFY trigger (reemplaza polling cada 3s y 5s)
--    [4] Sin foreign keys a club_miembros — BDs separadas,
--        la integridad referencial la garantiza mensaje_api.py
-- ============================================================


-- ============================================================
--  TIPOS ENUM  (mejora #1)
-- ============================================================

CREATE TYPE tipo_conversacion AS ENUM ('grupal', 'individual');


-- ============================================================
--  TABLAS
--  NOTA sobre IDs foráneos:
--  socio_id, evento_id, destinatario_id son INTEGER simples,
--  no tienen REFERENCES porque apuntan a club_miembros (otra BD).
--  mensaje_api.py es responsable de validar que existan.
-- ============================================================

CREATE TABLE conversaciones (
    id              SERIAL              PRIMARY KEY,
    evento_id       INTEGER             NOT NULL,   -- FK lógica → club_miembros.eventos.id
    nombre_conv     VARCHAR(200)        NOT NULL,
    tipo_conv       tipo_conversacion   NOT NULL,   -- mejora #1: era VARCHAR libre
    participante_a  INTEGER             NOT NULL,   -- FK lógica → club_miembros.miembros.id
    participante_b  INTEGER                         -- FK lógica → club_miembros.miembros.id (NULL en grupal)
);

CREATE TABLE mensajes (
    id                  SERIAL          PRIMARY KEY,
    conversacion_id     INTEGER         NOT NULL    REFERENCES conversaciones(id) ON DELETE CASCADE,
    evento_id           INTEGER         NOT NULL,   -- FK lógica → club_miembros.eventos.id
    remitente_nombre    VARCHAR(200)    NOT NULL,
    destinatario_id     INTEGER,                    -- FK lógica → club_miembros.miembros.id (NULL en grupal)
    texto               TEXT            NOT NULL,
    timestamp           TIMESTAMP       NOT NULL    DEFAULT NOW(),  -- mejora #2: era TEXT
    leido               BOOLEAN         NOT NULL    DEFAULT FALSE,
    borrado             BOOLEAN         NOT NULL    DEFAULT FALSE,
    borrado_en          TIMESTAMP                                   -- mejora #2: era TEXT
);

CREATE TABLE ultima_lectura (
    socio_id            INTEGER     NOT NULL,   -- FK lógica → club_miembros.miembros.id
    conversacion_id     INTEGER     NOT NULL    REFERENCES conversaciones(id) ON DELETE CASCADE,
    visto_en            TIMESTAMP   NOT NULL,
    PRIMARY KEY (socio_id, conversacion_id)
);


-- ============================================================
--  NOTIFY TRIGGER  (mejora #3)
--  Cuando se inserta un mensaje, Postgres avisa al servidor
--  por el canal 'mensaje_nuevo'. actualizador.py escucha con
--  LISTEN y empuja el dato al frontend por WebSocket.
--
--  Archivos que cambian por esto:
--    - actualizador.py → agregar LISTEN + WebSocket
--    - INDEX.HTML      → reemplazar setInterval por WebSocket
--    - mensaje_api.py  → sin cambio, el trigger es automático
-- ============================================================

CREATE OR REPLACE FUNCTION notificar_mensaje_nuevo()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify(
        'mensaje_nuevo',
        json_build_object(
            'conversacion_id',  NEW.conversacion_id,
            'evento_id',        NEW.evento_id,
            'destinatario_id',  NEW.destinatario_id,
            'timestamp',        NEW.timestamp
        )::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_mensaje_nuevo
AFTER INSERT ON mensajes
FOR EACH ROW EXECUTE FUNCTION notificar_mensaje_nuevo();


-- ============================================================
--  ÍNDICES
-- ============================================================

CREATE INDEX idx_mensajes_conv          ON mensajes(conversacion_id);
CREATE INDEX idx_mensajes_destinatario  ON mensajes(destinatario_id, leido);
CREATE INDEX idx_ultima_lectura_socio   ON ultima_lectura(socio_id);
