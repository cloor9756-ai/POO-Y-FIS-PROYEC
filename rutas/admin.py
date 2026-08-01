from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps

admin = Blueprint('admin', __name__)

def login_requerido(f):
    @wraps(f)
    def funcion_decorada(*args, **kwargs):
        # Si la variable 'logeado' no existe en la sesión, los expulsa al login
        if not session.get('logeado'):
            flash('Por favor, inicia sesión para acceder al sistema.', 'error')
            return redirect(url_for('admin.enlogin'))
        return f(*args, **kwargs)
    return funcion_decorada

@admin.route('/login', methods=['GET', 'POST'])
def enlogin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        from app import mysql
        cursor = mysql.connection.cursor()
        
        # 1. Consultamos seleccionando las columnas explícitas para evitar problemas de índices
        cursor.execute("""
            SELECT id, username, password, rol 
            FROM usuarios 
            WHERE username = %s AND password = %s
        """, (username, password))
        
        usuario_encontrado = cursor.fetchone()
        cursor.close()
        
        if usuario_encontrado:
            # 2. Guardamos los datos de la tupla de manera segura usando strings limpios
            session['logeado'] = True
            session['id_usuario'] = int(usuario_encontrado[0])
            session['usuario'] = str(usuario_encontrado[1])
            
            # Limpiamos el rol de cualquier espacio en blanco o mayúscula inesperada
            rol_usuario = str(usuario_encontrado[3]).strip().capitalize()
            session['rol'] = rol_usuario 
            
            # 3. REDIRECCIÓN INTELIGENTE SEGÚN EL ROL DETECTADO (Corregido dentro del bloque IF)
            if rol_usuario == 'Cliente':
                return redirect(url_for('admin.dashboard_cliente'))
            elif rol_usuario == 'Administrador' or rol_usuario == 'Admin':
                return redirect(url_for('admin.dashboard'))
            else:
                flash('Rol no reconocido en el sistema.', 'error')
                return redirect(url_for('admin.enlogin'))
        else:
            # Alerta si las credenciales no coinciden en la base de datos
            flash('Usuario o contraseña incorrectos. Verifica tus datos.', 'error')
            return redirect(url_for('admin.enlogin'))
            
    return render_template('index.html')

@admin.route('/dashboard-cliente')
def dashboard_cliente():
    # Protección de ruta: Validar que esté logeado y sea un cliente
    if not session.get('logeado') or session.get('rol') != 'Cliente':
        return redirect(url_for('admin.enlogin'))
        
    # Renderiza la interfaz exclusiva del cliente pasando su nombre de usuario
    return render_template('admin/dashboard-cliente.html', usuario=session.get('usuario'))

@admin.route('/dashboard')
@login_requerido
def dashboard():
    from app import mysql
    if not session.get('logeado'):
        return redirect(url_for('admin.enlogin'))
        
    # 1. Inicializamos el cursor en None para evitar que se rompa el "finally"
    cursor = None
    
    try:
        cursor = mysql.connection.cursor()
        
        # 2. Traer usuarios
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
        flash(f"Error en la base de datos dentro del Dashboard: {str(e)}", "error")
        return render_template("admin/dashboard.html", usuarios=[], pedidos=[], maquinarias=[])
        
    finally:
        # 5. Protección definitiva: solo cierra si el cursor se logró crear y sigue abierto
        if cursor is not None and cursor:
            cursor.close()

@admin.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.enlogin'))

@admin.route('/crear-pedido', methods=['POST'])
def crear_pedido():
    # 1. Validamos que el cliente haya iniciado sesión de forma correcta
    if not session.get('logeado'):
        return redirect(url_for('admin.enlogin'))
        
    # 2. Capturamos los datos enviados por los menús desplegables y el input numérico
    costo_material = float(request.form.get('material', 0))
    costo_transporte = float(request.form.get('tarifa_zona', 0))
    horas_retro = float(request.form.get('horas_retro') or 0)
    
    # 3. Aplicamos la regla de negocio para el costo de maquinaria
    costo_maquinaria = 0.0
    if horas_retro > 0:
        if horas_retro < 2:
            horas_retro = 2.0  # Cobro mínimo establecido
        costo_maquinaria = horas_retro * 40.0
        
    # 4. Calculamos el monto total final de la cotización
    total_final = costo_material + costo_transporte + costo_maquinaria
    
    # 5. Insertamos de forma segura los valores en la base de datos
    from app import mysql
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO pedidos (costo_material, costo_transporte, costo_maquinaria, total) 
            VALUES (%s, %s, %s, %s)
        """, (costo_material, costo_transporte, costo_maquinaria, total_final))
        
        mysql.connection.commit()
        flash("¡Tu cotización y pedido han sido procesados con éxito!", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al procesar el pedido en el sistema: {str(e)}", "error")
    finally:
        cursor.close()
        
    return redirect(url_for('admin.dashboard_cliente'))


@admin.route('/actualizar-maquinaria', methods=['POST'])
def actualizar_maquinaria():
    from app import mysql
    if not session.get('logeado'):
        return redirect(url_for('admin.enlogin'))
        
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

# ELIMINAR USUARIOS 
@admin.route('/eliminar-usuario/<int:id_usuario>', methods=['POST'])
@login_requerido
def eliminar_usuario(id_usuario):
    from app import mysql
    if session.get('usuario') == request.form.get('username_eliminar'):
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

# AÑADIR USUARIOS (Completado y Corregido)
@admin.route('/crear-usuario', methods=['POST'])
@login_requerido
def crear_usuario():
    from app import mysql
    
    nuevo_usuario = request.form.get('username')
    nueva_contrasena = request.form.get('password')
    rol_asignado = request.form.get('rol', 'Cliente') # Por defecto asigna Cliente si no viene en el form
    
    if not nuevo_usuario or not nueva_contrasena:
        flash("Todos los campos son obligatorios", "error")
        return redirect(url_for('admin.dashboard'))
        
    cursor = mysql.connection.cursor()
    try:
        # Validación extra: Verificar que el nombre de usuario no esté repetido
        cursor.execute("SELECT id FROM usuarios WHERE username = %s", (nuevo_usuario,))
        if cursor.fetchone():
            flash("El nombre de usuario ya se encuentra registrado.", "error")
            return redirect(url_for('admin.dashboard'))
            
        # Inserción del nuevo usuario
        cursor.execute("""
            INSERT INTO usuarios (username, password, rol) 
            VALUES (%s, %s, %s)
        """, (nuevo_usuario, nueva_contrasena, rol_asignado))
        
        mysql.connection.commit()
        flash("Usuario administrativo creado con éxito.", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al crear el usuario: {str(e)}", "error")
    finally:
        cursor.close()
        
    return redirect(url_for('admin.dashboard'))
