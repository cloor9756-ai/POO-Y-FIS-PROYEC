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
