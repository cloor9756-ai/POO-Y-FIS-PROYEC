from flask import Blueprint, render_template, request, redirect, url_for, flash, session

admin = Blueprint('admin', __name__)
from functools import wraps

def login_requerido(f):
    @wraps(f)
    def funcion_decorada(*args, **kwargs):
        # Si la variable 'logeado' no existe en la sesión, los expulsa al login
        if not session.get('logeado'):
            flash('Por favor, inicia sesión para acceder al sistema.', 'error')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return funcion_decorada

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
@login_requerido
def dashboard():
    from app import mysql
    if not session.get('logeado'):
        return redirect(url_for('admin.login'))
        
    # 1. Inicializamos el cursor en None para evitar que se rompa el "finally"
    cursor = None
    
    try:
        cursor = mysql.connection.cursor()
        
        # 2. Traer usuarios (Si te da error aquí, verifica que tu tabla 'usuarios' tenga la columna 'rol')
        cursor.execute("SELECT id, username, rol FROM usuarios")
        lista_usuarios = cursor.fetchall()
        
        # 3. Traer pedidos
        cursor.execute("SELECT id, costo_material, costo_transporte, costo_maquinaria, total FROM pedidos ORDER BY id DESC")
        lista_pedidos = cursor.fetchall()
        
        # 4. Traer maquinaria
        cursor.execute("SELECT id, codigo_maquina, tipo, estado, horas_totales FROM maquinaria")
        lista_maquinaria = cursor.fetchall()
        
        # Si todo sale bien, cerramos aquí mismo de forma segura
        cursor.close()
        cursor = None # Lo volvemos None para que el finally no intente duplicar el cierre
        
        return render_template(
            "admin/dashboard.html", 
            usuarios=lista_usuarios, 
            pedidos=lista_pedidos, 
            maquinarias=lista_maquinaria
        )
        
    except Exception as e:
        # Si algo falla (como que no encuentre la columna 'rol'), te mandará este mensaje limpio
        flash(f"Error en la base de datos dentro del Dashboard: {str(e)}", "error")
        # Retornamos la plantilla con listas vacías para que la interfaz cargue y no se quede congelada
        return render_template("admin/dashboard.html", usuarios=[], pedidos=[], maquinarias=[])
        
    finally:
        # 5. Protección definitiva: solo cierra si el cursor se logró crear y sigue abierto
        if cursor is not None and cursor:
            cursor.close()



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

#ELIMINAR USUARIOS 
@admin.route('/eliminar-usuario/<int:id_usuario>', methods=['POST'])
@login_requerido
def eliminar_usuario(id_usuario):
    from app import mysql
    # Regla de negocio: Evitar que el administrador se elimine a sí mismo
    if session.get('username') == request.form.get('username_eliminar'):
        flash('No puedes eliminar tu propia cuenta de usuario en sesión.', 'error')
        return redirect(url_for('admin.dashboard'))

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (id_usuario,))
        mysql.connection.commit()
        flash('Usuario eliminado del sistema correctamente.', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error al eliminar el usuario: {str(e)}', 'error')
    finally:
        cursor.close()
        
    return redirect(url_for('admin.dashboard'))
#AÑADIR USUSRAIOS
@admin.route('/crear-usuario', methods=['POST'])
def crear_usuario():
    from app import mysql
    if not session.get('logeado'):
        return redirect(url_for('admin.login'))
        
    nuevo_usuario = request.form.get('username')
    nueva_contrasena = request.form.get('password')
    
    if not nuevo_usuario or not nueva_contrasena:
        flash("Todos los campos son obligatorios", "error")
        return redirect(url_for('admin.dashboard'))
        
    cursor = mysql.connection.cursor()
    try:
        # Validación extra: Verificar que el nombre de usuario no esté repetido
        cursor.execute("SELECT id FROM usuarios WHERE username = %s", (nuevo_usuario,))
        if cursor.fetchone():
            flash("El nombre de usuario ya se encuentra registrado", "error")
            return redirect(url_for('admin.dashboard'))
            
        # Inserción en la base de datos (Estructura: username, password)
        cursor.execute("""
            INSERT INTO usuarios (username, password) 
            VALUES (%s, %s)
        """, (nuevo_usuario, nueva_contrasena))
        
        mysql.connection.commit()
        flash(f"Usuario '{nuevo_usuario}' registrado con éxito", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al registrar el usuario: {str(e)}", "error")
    finally:
        cursor.close()
        
    return redirect(url_for('admin.dashboard'))

    #AQUI SE CRA EL USUARIO
    @admin.route('/crear-usuario', methods=['POST'])
    def crear_usuario():
        from app import mysql
    if not session.get('logeado'):
        return redirect(url_for('admin.login'))
        
    # 1. INICIALIZAMOS EN NONE PARA EVITAR EL ERROR DE LA CAPTURA
    cursor = None 
    
    nuevo_usuario = request.form.get('username')
    nueva_contrasena = request.form.get('password')
    rol_seleccionado = request.form.get('rol')
    
    try:
        # Aquí es donde realmente se le asigna un valor a la variable
        cursor = mysql.connection.cursor()
        
        cursor.execute("SELECT id FROM usuarios WHERE username = %s", (nuevo_usuario,))
        if cursor.fetchone():
            flash("El nombre de usuario ya se encuentra registrado", "error")
            return redirect(url_for('admin.dashboard'))
            
        cursor.execute("""
            INSERT INTO usuarios (username, password, rol) 
            VALUES (%s, %s, %s)
        """, (nuevo_usuario, nueva_contrasena, rol_seleccionado))
        
        mysql.connection.commit()
        flash(f"Usuario registrado con éxito", "success")
        
    except Exception as e:
        if cursor:
            mysql.connection.rollback()
        flash(f"Error al registrar: {str(e)}", "error")
        
    finally:
        # 2. SOLO SE CIERRA SI EL CURSOR EXISTE Y NO ES NONE
        if cursor is not None and cursor: 
            cursor.close()
            
    return redirect(url_for('admin.dashboard'))