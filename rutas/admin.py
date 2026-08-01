from flask import Blueprint, render_template, request, redirect, url_for, flash, session

admin = Blueprint('admin', __name__)
from functools import wraps

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
            
            # 3. REDIRECCIÓN COMPARANDO EL TEXTO LIMPIO
            if rol_usuario == 'Cliente':
                return redirect(url_for('admin.dashboard_cliente'))
            else:
                return redirect(url_for('admin.dashboard'))
        else:
            # 4. Alerta si las credenciales no coinciden en la base de datos
            flash("Usuario o contraseña incorrectos. Verifica los datos en tu base de datos.", "error")
            return redirect(url_for('admin.enlogin'))
            
    return render_template('index.html')

@admin.route('/dashboard-cliente')
def dashboard_cliente():
    # Protección de ruta: Validar que esté logeado y sea un cliente
    if not session.get('logeado') or session.get('rol') != 'Cliente':
        return redirect(url_for('admin.enlogin'))
        
    # Renderiza la interfaz exclusiva del cliente pasando su nombre de usuario
    return render_template('admin/dashboard_cliente.html', usuario=session.get('usuario'))

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
    return redirect(url_for('admin.enlogin'))



@admin.route('/crear-pedido', methods=['POST']) # O el nombre exacto que le diste a tu ruta de registro
def registrar_usuario_cliente():
    username = request.form.get('username')
    password = request.form.get('password')
    
    from app import mysql
    cursor = mysql.connection.cursor()
    try:
        # Forzamos que guarde el valor 'Cliente' en la columna 'rol'
        cursor.execute("""
            INSERT INTO usuarios (username, password, rol) 
            VALUES (%s, %s, %s)
        """, (username, password, 'Cliente'))
        
        mysql.connection.commit()
        flash("¡Registro exitoso como Cliente!", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al registrar: {str(e)}", "error")
    finally:
        cursor.close()
        
    return redirect(url_for('admin.enlogin'))


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
        return redirect(url_for('admin.enlogin'))
        
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
        return redirect(url_for('admin.enlogin'))
        
        
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




    @admin.route('/registrar-cliente', methods=['POST'])
    def registrar_cliente():
        from app import mysql
    
    usuario = request.form.get('username')
    contrasena = request.form.get('password')
    direccion = request.form.get('direccion')
    
    if not usuario or not contrasena or not direccion:
        flash("Todos los campos son obligatorios para el registro", "error")
        return redirect(url_for('admin.enlogin'))
        
    cursor = mysql.connection.cursor()
    try:
        # Validación: Verificar que el cliente no exista ya
        cursor.execute("SELECT id FROM usuarios WHERE username = %s", (usuario,))
        if cursor.fetchone():
            flash("El nombre de usuario ya está en uso", "error")
            return redirect(url_for('admin.enlogin'))
            
        # Insertar con rol 'Cliente' automático y guardando su dirección (Historia 001)
        cursor.execute("""
            INSERT INTO usuarios (username, password, rol, direccion) 
            VALUES (%s, %s, 'Cliente', %s)
        """, (usuario, contrasena, direccion))
        
        mysql.connection.commit()
        flash("¡Registro exitoso! Ya puedes iniciar sesión.", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al registrar cliente: {str(e)}", "error")
    finally:
        if cursor:
            cursor.close()
            
    return redirect(url_for('admin.enlogin'))


