from flask import Flask
from flask_mysqldb import MySQL
from rutas.admin import admin

app = Flask(__name__)
# CORREGIDO: Ahora se configura antes de arrancar el servidor
app.secret_key = 'mi_clave_secreta_super_segura'

# Configuraciones de tu base de datos...
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'proyecto_fis_poo'

# 1. PASO CLAVE: Inicializamos el objeto de forma global
mysql = MySQL(app)

# 2. Registramos el blueprint DESPUÉS de inicializar mysql
app.register_blueprint(admin)

if __name__ == '__main__':
    app.run(debug=True)
