-- ============================================================
--  BLACKBELT CLUB -- Schema PostgreSQL
--  BASE DE DATOS: club_miembros
--  Migrado desde: club_miembros.db
--  Generado: 2026-05-10
--
--  MEJORAS SOBRE SQLITE:
--    [1] ENUM para estado de responsabilidades y roles
--    [2] Fechas como DATE / TIMESTAMP real (no TEXT)
--    [3] Foreign keys explícitas en todas las tablas
--    [4] password_hash + debe_cambiar_pass en miembros
-- ============================================================


-- ============================================================
--  TIPOS ENUM  (mejora #1)
-- ============================================================

CREATE TYPE estado_responsabilidad AS ENUM ('Pendiente', 'En curso', 'Completado');
CREATE TYPE rol_jerarquia           AS ENUM ('Director', 'Coordinador', 'Colaborador');


-- ============================================================
--  TABLAS
-- ============================================================

CREATE TABLE categorias (
    id      SERIAL          PRIMARY KEY,
    nombre  VARCHAR(100)    NOT NULL
);

CREATE TABLE miembros (
    id                  SERIAL          PRIMARY KEY,
    nombres             VARCHAR(100)    NOT NULL,
    apellidos           VARCHAR(100)    NOT NULL,
    cedula              VARCHAR(20)     UNIQUE,
    telefono            VARCHAR(20),
    direccion           TEXT,
    correo              VARCHAR(150),
    fecha_ingreso       DATE,                          -- mejora #2: era TEXT
    categoria           VARCHAR(100),
    ciudad_nacimiento   VARCHAR(100),
    fecha_nacimiento    DATE,                          -- mejora #2: era TEXT
    genero              VARCHAR(20),
    password_hash       VARCHAR(255)    NOT NULL    DEFAULT '',  -- mejora #4
    debe_cambiar_pass   BOOLEAN         NOT NULL    DEFAULT TRUE -- mejora #4
);

CREATE TABLE historial (
    id              SERIAL      PRIMARY KEY,
    socio_id        INTEGER     NOT NULL    REFERENCES miembros(id) ON DELETE CASCADE,
    fecha_suceso    DATE,                              -- mejora #2: era TEXT
    descripcion     TEXT
);

CREATE TABLE eventos (
    id          SERIAL          PRIMARY KEY,
    nombre      VARCHAR(200)    NOT NULL,
    fecha       DATE,                                  -- mejora #2: era TEXT
    descripcion TEXT
);

CREATE TABLE evento_participantes (
    id          SERIAL      PRIMARY KEY,
    evento_id   INTEGER     NOT NULL    REFERENCES eventos(id)  ON DELETE CASCADE,
    socio_id    INTEGER     NOT NULL    REFERENCES miembros(id) ON DELETE CASCADE,
    UNIQUE (evento_id, socio_id)
);

CREATE TABLE jerarquia_roles (
    id              SERIAL          PRIMARY KEY,
    evento_id       INTEGER         NOT NULL    REFERENCES eventos(id)  ON DELETE CASCADE,
    socio_id        INTEGER         NOT NULL    REFERENCES miembros(id) ON DELETE CASCADE,
    rol             rol_jerarquia   NOT NULL,           -- mejora #1: era VARCHAR libre
    coordinador_id  INTEGER                     REFERENCES miembros(id) ON DELETE SET NULL,
    UNIQUE (evento_id, socio_id)
);

CREATE TABLE responsabilidades (
    id              SERIAL                  PRIMARY KEY,
    evento_id       INTEGER                 NOT NULL    REFERENCES eventos(id)  ON DELETE CASCADE,
    socio_id        INTEGER                 NOT NULL    REFERENCES miembros(id) ON DELETE CASCADE,
    descripcion     TEXT                    NOT NULL,
    fecha_limite    DATE,                              -- mejora #2: era TEXT
    estado          estado_responsabilidad  NOT NULL    DEFAULT 'Pendiente'     -- mejora #1: era VARCHAR libre
);

CREATE TABLE checklist_items (
    id                  SERIAL      PRIMARY KEY,
    responsabilidad_id  INTEGER     NOT NULL    REFERENCES responsabilidades(id) ON DELETE CASCADE,
    texto               TEXT        NOT NULL,
    completado          BOOLEAN     NOT NULL    DEFAULT FALSE
);


-- ============================================================
--  ÍNDICES
-- ============================================================

CREATE INDEX idx_miembros_cedula        ON miembros(cedula);
CREATE INDEX idx_jerarquia_socio        ON jerarquia_roles(socio_id);
CREATE INDEX idx_jerarquia_evento       ON jerarquia_roles(evento_id);
CREATE INDEX idx_resp_evento_socio      ON responsabilidades(evento_id, socio_id);
CREATE INDEX idx_checklist_resp         ON checklist_items(responsabilidad_id);
