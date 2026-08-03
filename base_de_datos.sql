CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    rol VARCHAR(50) DEFAULT 'Administrador'
);


INSERT INTO usuarios (username, password, rol)
VALUES ('admin','1234','Administrador');


CREATE TABLE materiales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT
);


CREATE TABLE zonas_tarifas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    zona VARCHAR(100) NOT NULL,
    tarifa DECIMAL(10,2) NOT NULL
);


CREATE TABLE volquetas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    clase VARCHAR(50) NOT NULL,
    placa VARCHAR(20) UNIQUE NOT NULL,
    capacidad DECIMAL(10,2) NOT NULL,
    disponible BOOLEAN DEFAULT TRUE,
    operador_id INT NULL,
    FOREIGN KEY (operador_id) REFERENCES usuarios(id)
);


CREATE TABLE maquinaria (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_maquina VARCHAR(50) NOT NULL UNIQUE,
    tipo VARCHAR(100) DEFAULT 'Retroexcavadora',
    estado VARCHAR(50) DEFAULT 'Disponible',
    horas_totales INT DEFAULT 0,
    placa VARCHAR(20),
    capacidad DECIMAL(10,2)
);


CREATE TABLE pedidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    costo_material DECIMAL(10,2) NOT NULL,
    costo_transporte DECIMAL(10,2) NOT NULL,
    costo_maquinaria DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    estado VARCHAR(50) DEFAULT 'Confirmado',
    operador_id INT NULL,
    volqueta_id INT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (operador_id) REFERENCES usuarios(id),
    FOREIGN KEY (volqueta_id) REFERENCES volquetas(id)
);