from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import mysql  # Importación global para limpiar las funciones

admin = Blueprint('admin', __name__)

@admin.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['username']
        contrasena = request.form['password']
        
        cursor = mysql.connection.cursor()
        # Nota: Idealmente deberías usar contraseñas encriptadas con Werkzeug en el futuro
        cursor.execute("SELECT * FROM usuarios WHERE username = %s AND password = %s", (usuario, contrasena))
        cuenta = cursor.fetchone()
        cursor.close()
        
        if cuenta:
            session['logeado'] = True
            session['username'] = usuario
            
            # Ajusta el índice según el orden de tus columnas en base_de_datos.sql
            # Por ejemplo: id(0), username(1), password(2), email(3), tipo_usuario(4)
            session['tipo_usuario'] = cuenta[4] if len(cuenta) > 4 else 'Administrador'
            
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            return redirect(url_for('admin.login'))
            
    return render_template("index.html")


@admin.route('/dashboard')
def dashboard():
    if not session.get('logeado'):
        return redirect(url_for('admin.login'))
        
    cursor = mysql.connection.cursor()
    # Modificamos la consulta para devolver 'Administrador' como una tercera columna fija
    # ya que tu tabla actual de MySQL solo tiene: id, username, password.
    cursor.execute("SELECT id, username, 'Administrador' AS rol FROM usuarios") 
    lista_usuarios = cursor.fetchall()
    cursor.close()
    
    # Se los enviamos con el mismo nombre que usas en el bucle {% for usuario in usuarios %}
    return render_template("admin/dashboard.html", usuarios=lista_usuarios)


@admin.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.login'))
