from flask import Blueprint, render_template, request, redirect, url_for, flash, session

admin = Blueprint('admin', __name__)

@admin.route('/login', methods=['GET', 'POST'])
def login():
    from app import mysql
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
    from app import mysql
    if not session.get('logeado'):
        return redirect(url_for('admin.login'))
        
    cursor = mysql.connection.cursor()
    
    # 1. Traer usuarios para la pestaña de Control Personal
    cursor.execute("SELECT id, username, 'Administrador' AS rol FROM usuarios") 
    lista_usuarios = cursor.fetchall()
    
    # 2. Traer pedidos para la pestaña de Pedidos Material (EVITA PANTALLA VACÍA)
    cursor.execute("SELECT id, costo_material, costo_transporte, costo_maquinaria, total FROM pedidos ORDER BY id DESC")
    lista_pedidos = cursor.fetchall()
    
    # 3. Traer maquinaria para la pestaña de Retroexcavadoras (EVITA PANTALLA VACÍA)
    cursor.execute("SELECT id, codigo_maquina, tipo, estado, horas_totales FROM maquinaria")
    lista_maquinaria = cursor.fetchall()
    
    cursor.close()
    
    # Se envían todas las listas al HTML para que cada pestaña tenga sus datos listos
    return render_template(
        "admin/dashboard.html", 
        usuarios=lista_usuarios, 
        pedidos=lista_pedidos, 
        maquinarias=lista_maquinaria
    )


@admin.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.login'))


@admin.route('/crear-pedido', methods=['POST'])
def crear_pedido():
    from app import mysql
    if not session.get('logeado'):
        return redirect(url_for('admin.login'))
    
    # 1. Recuperar los datos del formulario HTML
    costo_material = float(request.form.get('material', 0))
    tarifa_zona = float(request.form.get('tarifa_zona', 0))
    horas_retro = float(request.form.get('horas_retro', 0))
    tarifa_hora_retro = 40.0  # Costo fijo de la retroexcavadora por hora

    # 2. CAPA DE LÓGICA DE NEGOCIO (Reglas de cálculo)
    costo_pedido = costo_material + tarifa_zona
    
    # Aplicar la regla de negocio: mínimo 2 horas si se utiliza maquinaria pesada
    if horas_retro > 0:
        horas_efectivas = max(horas_retro, 2)
        costo_retro = horas_efectivas * tarifa_hora_retro
    else:
        costo_retro = 0.0

    costo_total_final = costo_pedido + costo_retro

    # 3. Conexión y almacenamiento en base de datos
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO pedidos (costo_material, costo_transporte, costo_maquinaria, total) 
            VALUES (%s, %s, %s, %s)
        """, (costo_material, tarifa_zona, costo_retro, costo_total_final))
        
        mysql.connection.commit()
        flash(f"¡Pedido guardado! Costo Total calculado: ${costo_total_final:.2f}", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al registrar pedido en la base de datos: {str(e)}", "error")
    finally:
        cursor.close()

    return redirect(url_for('admin.dashboard'))


@admin.route('/actualizar-maquinaria', methods=['POST'])
def actualizar_maquinaria():
    from app import mysql
    if not session.get('logeado'):
        return redirect(url_for('admin.login'))
        
    id_maquina = request.form.get('id_maquina')
    nuevo_estado = request.form.get('estado')
    horas_nuevas = int(request.form.get('horas_nuevas', 0))
    
    cursor = mysql.connection.cursor()
    try:
        # Actualizamos el estado y sumamos las horas de uso acumuladas
        cursor.execute("""
            UPDATE maquinaria 
            SET estado = %s, horas_totales = horas_totales + %s 
            WHERE id = %s
        """, (nuevo_estado, horas_nuevas, id_maquina))
        
        mysql.connection.commit()
        flash("Maquinaria actualizada correctamente", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al actualizar la maquinaria: {str(e)}", "error")
    finally:
        cursor.close()
        
    return redirect(url_for('admin.dashboard'))
