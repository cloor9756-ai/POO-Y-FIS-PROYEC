from flask import Flask
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = 'mi_clave_secreta_super_segura'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'proyecto_fis_poo'

# 1. Inicialización correcta con Mayúscula
mysql = MySQL(app)

# 2. Importación del módulo de rutas
from rutas.admin import admin
app.register_blueprint(admin)

if __name__ == '__main__':
    app.run(debug=True)
