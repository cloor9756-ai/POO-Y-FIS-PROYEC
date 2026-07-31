CREATE TABLE IF NOT EXISTS pedidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    costo_material DECIMAL(10,2) NOT NULL,
    costo_transporte DECIMAL(10,2) NOT NULL,
    costo_maquinaria DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Asegurémonos de tener también la de maquinaria (corregida sin la "s" al final)
CREATE TABLE IF NOT EXISTS maquinaria (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_maquina VARCHAR(50) NOT NULL UNIQUE,
    tipo VARCHAR(100) DEFAULT 'Retroexcavadora',
    estado VARCHAR(50) DEFAULT 'Disponible',
    horas_totales INT DEFAULT 0
);

-- 3. Insertar datos de prueba para la maquinaria
INSERT INTO maquinaria (codigo_maquina, tipo, estado, horas_totales) 
VALUES ('RETRO-01', 'Retroexcavadora', 'Disponible', 120)
ON DUPLICATE KEY UPDATE codigo_maquina=codigo_maquina;

INSERT INTO maquinaria (codigo_maquina, tipo, estado, horas_totales) 
VALUES ('RETRO-02', 'Retroexcavadora', 'En Servicio', 340)
ON DUPLICATE KEY UPDATE codigo_maquina=codigo_maquina;