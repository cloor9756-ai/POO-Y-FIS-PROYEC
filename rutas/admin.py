from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps

admin = Blueprint('admin', __name__)


def login_requerido(f):
    @wraps(f)
    def funcion_decorada(*args, **kwargs):
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
        
        cursor.execute("""
            SELECT id, username, password, rol 
            FROM usuarios 
            WHERE username = %s AND password = %s
        """, (username, password))
        
        usuario_encontrado = cursor.fetchone()
        cursor.close()
        
        if usuario_encontrado:
            session['logeado'] = True
            session['id_usuario'] = int(usuario_encontrado[0])
            session['usuario'] = str(usuario_encontrado[1])
            
            rol_usuario = str(usuario_encontrado[3]).strip().capitalize()
            session['rol'] = rol_usuario 
            
            if rol_usuario == 'Cliente':
                return redirect(url_for('admin.dashboard_cliente'))
            elif rol_usuario == 'Administrador' or rol_usuario == 'Admin':
                return redirect(url_for('admin.dashboard'))
            else:
                flash('Rol no reconocido en el sistema.', 'error')
                return redirect(url_for('admin.enlogin'))
        else:
            flash('Usuario o contraseña incorrectos. Verifica tus datos.', 'error')
            return redirect(url_for('admin.enlogin'))
            
    return render_template('index.html')


@admin.route('/dashboard-cliente')
def dashboard_cliente():
    if not session.get('logeado') or session.get('rol') != 'Cliente':
        return redirect(url_for('admin.enlogin'))
        
    from app import mysql
    cursor = mysql.connection.cursor()
    
    # NUEVO: Traer materiales y zonas dinámicamente para los dropdowns del cliente
    cursor.execute("SELECT nombre, descripcion FROM materiales")
    lista_materiales = cursor.fetchall()
    
    cursor.execute("SELECT zona, tarifa FROM zonas_tarifas")
    lista_zonas = cursor.fetchall()
    
    cursor.close()
        
    return render_template('admin/dashboard-cliente.html', 
                           usuario=session.get('usuario'), 
                           materiales=lista_materiales, 
                           zonas=lista_zonas)


@admin.route('/dashboard')
@login_requerido
def dashboard():
    from app import mysql
    
    if not session.get('logeado'):
        return redirect(url_for('admin.enlogin'))
        
    cursor = None
    
    try:
        cursor = mysql.connection.cursor()
        
        cursor.execute("SELECT id, username, rol FROM usuarios")
        lista_usuarios = cursor.fetchall()
        
        cursor.execute("""
            SELECT id, costo_material, costo_transporte, costo_maquinaria, total 
            FROM pedidos 
            ORDER BY id DESC
        """)
        lista_pedidos = cursor.fetchall()
        
        # MODIFICADO (Opción B): Traer maquinaria unificada incluyendo placa, capacidad y el nombre de su operador asignado
        cursor.execute("""
            SELECT m.id, m.codigo_maquina, m.tipo, m.estado, 
                   m.horas_totales, m.placa, m.capacidad, u.username 
            FROM maquinaria m
            LEFT JOIN usuarios u ON m.operador_id = u.id
        """)
        lista_maquinaria = cursor.fetchall()


        # NUEVO: Traer Catálogo de Materiales para el Administrador
        cursor.execute("SELECT id, nombre_material, precio_m3 FROM materiales")

        lista_materiales = cursor.fetchall()


        # NUEVO: Traer Zonas y Tarifas para el Administrador
        cursor.execute("""
            SELECT id, zona, tarifa 
            FROM zonas_tarifas 
            ORDER BY id DESC
        """)
        lista_zonas = cursor.fetchall()


        # NUEVO: Traer los usuarios que tengan rol de Operador o Chofer
        cursor.execute("""
            SELECT id, username 
            FROM usuarios 
            WHERE rol LIKE '%chofer%' 
            OR rol LIKE '%operador%'
        """)
        lista_operadores = cursor.fetchall()


        cursor.close()
        cursor = None 
        
        return render_template(
            "admin/dashboard.html", 
            usuarios=lista_usuarios, 
            pedidos=lista_pedidos, 
            maquinarias=lista_maquinaria,
            materiales=lista_materiales,
            zonas=lista_zonas,
            operadores=lista_operadores
            
        )
        
    except Exception as e:
        flash(f"Error en la base de datos dentro del Dashboard: {str(e)}", "error")
        return render_template(
            "admin/dashboard.html",
            usuarios=[],
            pedidos=[],
            maquinarias=[],
            materiales=[],
            zonas=[],
            operadores=[]
        )
        
    finally:
        if cursor is not None:
            cursor.close()



@admin.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin.enlogin'))


#RUTA PARA CREAR PEDIDO DESDE EL DASHBOARD DEL CLIENTE
@admin.route('/crear-pedido', methods=['POST'])
def crear_pedido():
    if not session.get('logeado'):
        return redirect(url_for('admin.enlogin'))
        
    # Recibe los costos directamente calculados o seleccionados del cliente
    costo_material = float(request.form.get('material', 0))
    costo_transporte = float(request.form.get('tarifa_zona', 0))
    horas_retro = float(request.form.get('horas_retro') or 0)
    
    costo_maquinaria = 0.0
    
    if horas_retro > 0:
        if horas_retro < 2:
            horas_retro = 2.0
            
        costo_maquinaria = horas_retro * 40.0
        
    total_final = costo_material + costo_transporte + costo_maquinaria
    
    
    from app import mysql
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO pedidos 
            (costo_material, costo_transporte, costo_maquinaria, total) 
            VALUES (%s, %s, %s, %s)
        """, 
        (costo_material, costo_transporte, costo_maquinaria, total_final))
        
        
        mysql.connection.commit()
        flash("¡Tu cotización y pedido han sido procesados con éxito!", "success")
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al procesar el pedido en el sistema: {str(e)}", "error")
        
    finally:
        cursor.close()
        
    return redirect(url_for('admin.dashboard_cliente'))


# NUEVA RUTA: ACTUALIZAR ESTADO Y HORAS DE MAQUINARIA NO FUNCIONAL TOAVIA
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
        cursor.execute("""
            UPDATE maquinaria 
            SET estado = %s, horas_totales = horas_totales + %s 
            WHERE id = %s
        """, 
        (nuevo_estado, horas_nuevas, id_maquina))
        
        mysql.connection.commit()
        flash("Maquinaria actualizada correctamente", "success")
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al actualizar la maquinaria: {str(e)}", "error")
        
    finally:
        cursor.close()
        
    return redirect(url_for('admin.dashboard'))

# NUEVA RUTA: ASIGNAR OPERADOR ESPECÍFICO A MAQUINARIA/VOLQUETA
@admin.route('/asignar-operador', methods=['POST'])
@login_requerido
def asignar_operador():
    from app import mysql
    
    id_maquina = request.form.get('id_maquina')
    id_operador = request.form.get('id_operador')
    
    if id_operador == "":
        id_operador = None

    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute(
            "UPDATE maquinaria SET operador_id = %s WHERE id = %s",
            (id_operador, id_maquina)
        )
        
        mysql.connection.commit()
        flash("Operador asignado con éxito a la unidad.", "success")
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al asignar el operador: {str(e)}", "error")
        
    finally:
        cursor.close()
        
    return redirect(url_for('admin.dashboard'))


# NUEVA RUTA: GUARDAR NUEVO MATERIAL EN EL CATÁLOGO
@admin.route('/materiales/guardar', methods=['POST'])
@login_requerido
def guardar_material():
    from app import mysql

    nombre = request.form.get('nombre_material')
    precio = request.form.get('precio_m3')

    cursor = mysql.connection.cursor()

    try:
        # CORRECCIÓN: Se cambió 'nombre_materiales' por 'materiales'
        cursor.execute(
            """
            INSERT INTO materiales (nombre_material, precio_m3)
            VALUES (%s, %s)
            """,
            (nombre, precio)
        )

        mysql.connection.commit()
        flash("Material guardado en el catálogo.", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al guardar material: {str(e)}", "error")

    finally:
        cursor.close()

    return redirect(url_for('admin.dashboard'))

# NUEVA RUTA: ELIMINAR UN MATERIAL DEL CATÁLOGO
@admin.route('/eliminar-material', methods=['POST'])
@login_requerido
def eliminar_material():
    from app import mysql

    # Se obtiene el ID enviado desde el campo oculto (input hidden) del HTML
    id_material = request.form.get('id_material')

    cursor = mysql.connection.cursor()

    try:
        # Se ejecuta la sentencia SQL apuntando a la tabla correcta 'materiales'
        cursor.execute(
            "DELETE FROM materiales WHERE id = %s", 
            (id_material,)
        )

        mysql.connection.commit()
        flash("Material eliminado correctamente del catálogo.", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al eliminar el material: {str(e)}", "error")

    finally:
        cursor.close()

    # Redirige de vuelta al dashboard para actualizar la tabla visualmente
    return redirect(url_for('admin.dashboard'))

# NUEVA RUTA: GUARDAR NUEVA ZONA Y TARIFA
@admin.route('/zonas/guardar', methods=['POST'])
@login_requerido
def guardar_zona():
    from app import mysql

    # Primero obtener los datos
    nombre = request.form.get("nombre_zona")
    precio = request.form.get("tarifa")


    print(request.form)
    print("Zona:", nombre)
    print("Tarifa:", precio)

    # Luego validar
    if not nombre or not precio:
        flash("Todos los campos son obligatorios.", "error")
        return redirect(url_for('admin.dashboard'))

    cursor = mysql.connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO zonas_tarifas (zona, tarifa) VALUES (%s, %s)",
            (nombre, float(precio))
        )

        mysql.connection.commit()
        flash("Zona y tarifa añadidas con éxito.", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al registrar zona: {str(e)}", "error")

    finally:
        cursor.close()

    return redirect(url_for('admin.dashboard'))
#eliminar zona
@admin.route('/eliminar-zona', methods=['POST'])
@login_requerido
def eliminar_zona():
    from app import mysql
    
    id_zona = request.form.get('id_zona')
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute(
            "DELETE FROM zonas_tarifas WHERE id = %s",
            (id_zona,)
        )
        
        mysql.connection.commit()
        flash("Zona eliminada correctamente.", "success")
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al eliminar la zona: {str(e)}", "error")
        
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
        cursor.execute(
            "DELETE FROM usuarios WHERE id = %s",
            (id_usuario,)
        )
        
        mysql.connection.commit()
        flash('Usuario eliminado del sistema correctamente.', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error al eliminar el usuario: {str(e)}', 'error')
        
    finally:
        cursor.close()
        
    return redirect(url_for('admin.dashboard'))



# CREAR NUEVO USUARIO
@admin.route('/crear-usuario', methods=['POST'])
@login_requerido
def crear_usuario():
    from app import mysql
    
    username = request.form.get('username')
    password = request.form.get('password')
    rol = request.form.get('rol')
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO usuarios (username, password, rol) VALUES (%s, %s, %s)",
            (username, password, rol)
        )
        
        mysql.connection.commit()
        flash("Nuevo usuario registrado correctamente.", "success")
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al registrar usuario: {str(e)}", "error")
        
    finally:
        cursor.close()
        
    return redirect(url_for('admin.dashboard'))

#RUTA GUARDAR NUEVA MAQUINARIA/VOLQUETA
@admin.route('/maquinaria/guardar', methods=['POST'])
@login_requerido    
def guardar_maquinaria():
    from app import mysql
    
    codigo_maquina = request.form.get('codigo_maquina')
    tipo = request.form.get('tipo')
    estado = request.form.get('estado')
    horas_totales = int(request.form.get('horas_totales', 0))
    placa = request.form.get('placa')
    capacidad = float(request.form.get('capacidad', 0))
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO maquinaria 
            (codigo_maquina, tipo, estado, horas_totales, placa, capacidad) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, 
        (codigo_maquina, tipo, estado, horas_totales, placa, capacidad))
        
        mysql.connection.commit()
        flash("Maquinaria/Volqueta registrada correctamente.", "success")
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al registrar maquinaria: {str(e)}", "error")
        
    finally:
        cursor.close()
        
    return redirect(url_for('admin.dashboard'))
