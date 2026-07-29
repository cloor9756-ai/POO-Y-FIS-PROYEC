CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- Inserta un usuario de prueba para testear tu formulario
INSERT INTO usuarios (username, password) VALUES ('admin', '1234');
