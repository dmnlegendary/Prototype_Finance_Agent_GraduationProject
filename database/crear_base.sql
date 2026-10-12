-- Crea la base de datos y el usuario de marIA en PostgreSQL.
--
-- Cómo correrlo (en la terminal, desde la carpeta del proyecto):
--     psql -U postgres -f database/crear_base.sql
-- Antes cambia 'cambia_esta_clave' por la clave que quieras y usa la misma
-- en el archivo .env (variable DB_PASSWORD).

CREATE USER mariamiga WITH PASSWORD 'Arif+1812';

-- CREATEDB le permite a Django crear una base temporal cuando corremos las pruebas
ALTER USER mariamiga CREATEDB;

CREATE DATABASE maria_db
    OWNER mariamiga
    ENCODING 'UTF8'
    TEMPLATE template0;
