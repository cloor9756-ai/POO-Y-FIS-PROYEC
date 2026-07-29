from flask import Blueprint, render_template, request, redirect, url_for, flash, session

admin = Blueprint('admin', __name__)

@admin.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['username']
        contrasena = request.form['password']
        
        from app import mysql
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username = %s AND password = %s", (usuario, contrasena))
        cuenta = cursor.fetchone()
        cursor.close()
        
        if cuenta:
            # SEGURIDAD: Guardamos el usuario en la sesión activa
            session['logueado'] = True
            session['username'] = cuenta[1] # Guarda el nombre del usuario
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            return redirect(url_for('admin.login'))
            
    return render_template("accseso/index.html")

@admin.route('/dashboard')
def dashboard():
    # SEGURIDAD: Si no ha iniciado sesión, lo regresa al login
    if not session.get('logueado'):
        return redirect(url_for('admin.login'))
    return render_template("admin/dasboard.html")

@admin.route('/logout')
def logout():
    # Limpia la sesión y cierra el acceso
    session.clear()
    return redirect(url_for('admin.login'))
