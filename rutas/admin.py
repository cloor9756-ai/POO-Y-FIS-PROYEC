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
            session['logueado'] = True
            session['username'] = usuario
            session['tipo_usuario'] = cuenta[3] if len(cuenta) > 3 else 'Administrador'
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
            return redirect(url_for('admin.login'))
            
    return render_template("index.html")

@admin.route('/dashboard')
def dashboard():
    if not session.get('logueado'):
        return redirect(url_for('admin.login'))
        
    # Consultamos los usuarios de la base de datos de forma dinámica
    from app import mysql
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, username, rol FROM usuarios")
    lista_usuarios = cursor.fetchall()
    cursor.close()
    
    # Enviamos los datos recuperados a la plantilla HTML
    return render_template("admin/dashboard.html", usuarios=lista_usuarios)

@admin.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.login'))
