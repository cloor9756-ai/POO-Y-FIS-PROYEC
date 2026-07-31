from flask import current_app
from app import mysql


CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- Inserta un usuario de prueba para testear tu formulario
INSERT INTO usuarios (username, password) VALUES ('admin', '1234');

CREATE TABLE pedidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    costo_material DECIMAL(10,2) NOT NULL,
    costo_transporte DECIMAL(10,2) NOT NULL,
    costo_maquinaria DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS maquinaria;

-- 2. Crea la tabla correcta
CREATE TABLE maquinaria (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_maquina VARCHAR(50) NOT NULL UNIQUE,
    tipo VARCHAR(100) DEFAULT 'Retroexcavadora',
    estado VARCHAR(50) DEFAULT 'Disponible',
    horas_totales INT DEFAULT 0
);

-- 3. Inserta los datos de prueba limpios
INSERT INTO maquinaria (codigo_maquina, tipo, estado, horas_totales) VALUES 
('RETRO-01', 'Retroexcavadora', 'Disponible', 120),
('RETRO-02', 'Retroexcavadora', 'En Servicio', 340);

rol VARCHAR(50) DEFAULT "Administrador"

CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    rol VARCHAR(50) DEFAULT 'Administrador'
);
