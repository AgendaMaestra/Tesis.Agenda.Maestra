from flask import Flask, render_template, request, redirect, url_for, session, Response, flash, jsonify
import mysql.connector
from mysql.connector import pooling
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import base64
import hashlib
from functools import wraps
from datetime import date, datetime, timedelta
from datetime import date 
from datetime import datetime 
from datetime import datetime, timedelta 
from dotenv import load_dotenv
from flask_mail import Mail, Message
from flask_mail import Message, Mail

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'agenda_maestra_2026')

# --- CONFIGURACIÓN DE CORREO REFORZADA ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_ASCII_ATTACHMENTS'] = False

mail = Mail(app)

# ==========================================
# CONFIGURACIÓN DE BASE DE DATOS (POOL)
# ==========================================
db_config = {
    "host": os.getenv('DB_HOST', 'localhost'),
    "user": os.getenv('DB_USER', 'root'),
    "password": os.getenv('DB_PASSWORD', 'root'),
    "database": os.getenv('DB_NAME', 'agenda_maestra')
}

try:
    pool = pooling.MySQLConnectionPool(
        pool_name="agenda_pool",
        pool_size=10,
        **db_config
    )
except mysql.connector.Error as err:
    print(f"Error de conexión crítica: {err}")
    pool = None

def get_db():
    if pool is None:
        raise Exception("Base de datos no disponible")
    return pool.get_connection()

# ==========================================
# UTILIDADES Y DECORADORES
# ==========================================
def string_to_color(text):
    hash_obj = hashlib.md5(text.encode())
    hue = int(hash_obj.hexdigest(), 16) % 360
    return f"hsl({hue}, 75%, 60%)"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Debes iniciar sesión para acceder.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# SISTEMA DE EMAILS (BIENVENIDA Y NOTIFICACIONES)
# ==========================================
from datetime import datetime, timedelta
from flask import render_template
from flask_mail import Message

# --- MOTOR DE ENVÍOS (Lógica de fondo) ---

def enviar_correo(asunto, destinatario, plantilla_html):
    """Función genérica para enviar correos HTML"""
    try:
        msg = Message(asunto, recipients=[destinatario])
        msg.html = plantilla_html
        mail.send(msg)
    except Exception as e:
        print(f"Error enviando correo: {e}")

# --- FUNCIONES DE NOTIFICACIÓN ---

def enviar_bienvenida(email_usuario, nombre_usuario):
    """Envía el correo de bienvenida con el diseño avanzado y nuevas funciones"""
    try:
        msg = Message(
            f"¡Bienvenido a Agenda Maestra, {nombre_usuario}! 🚀",
            recipients=[email_usuario]
        )
        # Se intenta usar la plantilla profesional; si falla, usa el HTML embebido
        try:
            msg.html = render_template('emails/bienvenida.html', nombre=nombre_usuario)
        except:
            msg.html = f"""
            <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 40px; border-radius: 20px; max-width: 600px; margin: auto;">
                <h1 style="color: #38bdf8; text-align: center;">AGENDA<span style="color: #ffffff;">MAESTRA</span></h1>
                <p style="font-size: 1.1rem; line-height: 1.6;">¡Hola <strong>{nombre_usuario}</strong>! Gracias por unirte a la plataforma de organización más avanzada.</p>
                <div style="background: rgba(255,255,255,0.05); padding: 20px; border-radius: 15px; border: 1px solid #1e293b;">
                    <h3 style="color: #38bdf8; margin-top: 0;">¿Por qué usar Agenda Maestra?</h3>
                    <ul style="list-style: none; padding: 0;">
                        <li style="margin-bottom: 10px;">⭐ <b>Prioridad IA:</b> Ordenamos tus tareas por urgencia real.</li>
                        <li style="margin-bottom: 10px;">📈 <b>Gamificación:</b> Gana XP y sube de rango al completar deberes.</li>
                        <li style="margin-bottom: 10px;">♻️ <b>Papelera:</b> Tus archivos borrados viven 2 días más por seguridad.</li>
                    </ul>
                </div>
                <p style="text-align: center; margin-top: 30px;">
                    <a href="#" style="background: #38bdf8; color: #0f172a; padding: 12px 25px; border-radius: 10px; text-decoration: none; font-weight: bold;">EMPEZAR AHORA</a>
                </p>
            </div>
            """
        mail.send(msg)
    except Exception as e:
        print(f"Error enviando bienvenida: {e}")

def enviar_correo_notificacion(destinatario, usuario, tarea_tema, estado):
    """Notifica cambios inmediatos en el estado de una tarea específica"""
    try:
        # Usamos el timestamp para que Gmail no agrupe los correos en hilos
        ahora = datetime.now().strftime("%H:%M:%S")
        subject = f"Actualización: {tarea_tema} [{ahora}]"
        
        msg = Message(subject, recipients=[destinatario])
        msg.body = f"Hola {usuario},\n\nLa tarea '{tarea_tema}' ha sido marcada como {estado}.\n¡Sigue sumando XP en Agenda Maestra!\n\nID de notificación: {ahora}"
        mail.send(msg)
    except Exception as e:
        print(f"Error enviando notificación: {e}")

def verificar_recordatorios_proximos():
    """
    Busca tareas que vencen en 2 días y avisa al usuario.
    Incluye control de 'recordatorio_enviado' para evitar spam.
    """
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # 1. Calculamos la fecha de dentro de 2 días
        fecha_objetivo = (datetime.now() + timedelta(days=2)).date()
        
        # 2. Buscamos tareas que venzan en esa fecha, pendientes, no borradas
        # y que NO hayan sido notificadas aún (recordatorio_enviado = 0)
        cursor.execute("""
            SELECT t.*, u.email, u.usuario 
            FROM tareas t 
            JOIN usuarios u ON t.usuario_id = u.id 
            WHERE t.fecha = %s 
            AND t.estado = 'pendiente' 
            AND t.recordatorio_enviado = 0 
            AND t.eliminado_at IS NULL
        """, (fecha_objetivo,))
        
        proximas = cursor.fetchall()
        
        for tarea in proximas:
            try:
                # 3. Renderizado y envío del correo
                html = render_template('emails/recordatorio.html', tarea=tarea)
                enviar_correo(f"⏰ Recordatorio: {tarea['tema']} vence en 2 días", tarea['email'], html)
                
                # 4. Marcamos como enviado para no repetir el correo en la próxima carga
                cursor.execute("""
                    UPDATE tareas 
                    SET recordatorio_enviado = 1 
                    WHERE id = %s
                """, (tarea['id'],))
                
            except Exception as e_interno:
                print(f"Error procesando tarea individual {tarea['id']}: {e_interno}")
        
        # 5. Confirmamos los cambios de los UPDATES en la base de datos
        db.commit()
        
    except Exception as e:
        print(f"Error en verificar_recordatorios_proximos: {e}")
    finally:
        # 6. Siempre cerramos los recursos para evitar saturar el pool de conexiones
        if cursor: 
            cursor.close()
        if db: 
            db.close()

def notificar_logro(user_id, tipo_logro, valor):
    """Envía felicitaciones por alcanzar hitos, subir de nivel o racha"""
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT usuario, email FROM usuarios WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if user:
            html = render_template('emails/logro.html', 
                                   usuario=user['usuario'], 
                                   tipo=tipo_logro, 
                                   valor=valor)
            enviar_correo(f"🎉 ¡Felicidades! Nuevo logro alcanzado: {tipo_logro}", user['email'], html)
    except Exception as e:
        print(f"Error en notificar_logro: {e}")
    finally:
        if cursor: cursor.close()
        if db: db.close()

# ==========================================
# LÓGICA DE NIVELES Y GAMIFICACIÓN
# ==========================================
def obtener_rango(nivel):
    rangos = {1: "Novato", 5: "Estudiante Constante", 10: "Maestro de Tareas", 20: "Leyenda Académica"}
    rango_actual = "Principiante"
    for n in sorted(rangos.keys()):
        if nivel >= n: rango_actual = rangos[n]
    return rango_actual

def calcular_progreso_nivel(xp):
    nivel = (xp // 100) + 1
    xp_actual = xp % 100
    return nivel, xp_actual

# ==========================================
# IA / ALGORITMO DE PRIORIDAD
# ==========================================
def calcular_prioridad_ia(tarea):
    peso = 0
    hoy = date.today()
    f_tarea = tarea['fecha']
    if isinstance(f_tarea, str):
        try: f_tarea = datetime.strptime(f_tarea, '%Y-%m-%d').date()
        except: pass
    if isinstance(f_tarea, date):
        diferencia = (f_tarea - hoy).days
        if diferencia < 0: peso += 0 
        elif diferencia == 0: peso += 100 
        elif diferencia == 1: peso += 80  
        elif diferencia <= 3: peso += 50  
        elif diferencia <= 7: peso += 20
    if tarea.get('importante') == 1: peso += 50
    if tarea.get('tipo') == 'examen': peso += 30
    return peso

# --- FUNCIÓN DE APOYO: RECORDATORIOS ---
def verificar_recordatorios_pendientes(usuario_id, email_usuario):
    """Busca tareas próximas y envía un correo si cumplen el criterio."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # Buscamos tareas pendientes para hoy o mañana que NO estén en la papelera
        cursor.execute("""
            SELECT * FROM tareas 
            WHERE usuario_id = %s 
            AND estado = 'pendiente' 
            AND eliminado_at IS NULL
            AND fecha BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 1 DAY)
        """, (usuario_id,))
        
        tareas_proximas = cursor.fetchall()
        for tarea in tareas_proximas:
            # Nota: Idealmente aquí deberías marcar en la DB que ya notificaste 
            # esta tarea para no enviar el mail cada vez que el usuario entra al index.
            msg = Message(
                f"⏰ Recordatorio: {tarea['tema']}",
                recipients=[email_usuario]
            )
            msg.body = f"¡Hola! Te recordamos que la tarea '{tarea['tema']}' vence el {tarea['fecha']}. ¡No dejes que se te acumule el trabajo!"
            mail.send(msg)
    except Exception as e:
        print(f"Error en recordatorios: {e}")
    finally:
        cursor.close() # Cerramos cursor pero no la DB aquí si se usa fuera

# ==========================================
# RUTAS DE AUTENTICACIÓN
# ==========================================
@app.route('/login', methods=['GET','POST'])
def login():
    if 'user_id' in session: return redirect(url_for('index'))
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        password = request.form.get('password')
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE usuario=%s", (usuario,))
        user = cursor.fetchone()
        db.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session.permanent = True 
            flash(f"¡Bienvenido a Agenda Maestra, {user['usuario']}!", "success")
            return redirect(url_for('index'))
        flash("Credenciales inválidas.", "danger")
    return render_template("login.html")

@app.route('/registro', methods=['GET','POST'])
def registro():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        password = request.form.get('password')
        email = request.form.get('email', '')
        cumpleanos = request.form.get('cumpleanos') or None
        foto_archivo = request.files.get('foto_perfil')
        foto_base64 = None

        if foto_archivo and foto_archivo.filename != '':
            fileread = foto_archivo.read()
            encoded = base64.b64encode(fileread).decode('utf-8')
            foto_base64 = f"data:{foto_archivo.mimetype};base64,{encoded}"

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE usuario = %s", (usuario,))
        if cursor.fetchone():
            flash("Ese usuario ya existe.", "warning")
            db.close()
            return render_template("registro.html")

        hash_pass = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO usuarios(usuario, password, email, cumpleanos, foto_perfil, xp) VALUES(%s, %s, %s, %s, %s, 0)", 
            (usuario, hash_pass, email, cumpleanos, foto_base64)
        )
        nuevo_id = cursor.lastrowid
        db.commit()
        db.close()
        
        # EMAIL DE BIENVENIDA
        if email:
            enviar_bienvenida(email, usuario)

        session['user_id'] = nuevo_id
        session.permanent = True
        flash("¡Registro exitoso en Agenda Maestra!", "success")
        return redirect(url_for('index'))
    return render_template("registro.html")

# ==========================================
# RUTAS DE TAREAS
# ==========================================
# --- RUTA PRINCIPAL (INDEX) COMBINADA --
@app.route('/')
@login_required
def index():
    db = None
    cursor = None
    try:
        # 1. Inicialización y Limpieza de papelera (Automática)
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Eliminamos tareas que llevan más de 2 días en la papelera
        cursor.execute("DELETE FROM tareas WHERE eliminado_at < NOW() - INTERVAL 2 DAY")
        db.commit()

        # 2. Datos del usuario
        cursor.execute("SELECT usuario, email FROM usuarios WHERE id=%s", (session['user_id'],))
        user_data = cursor.fetchone()

        # 3. VERIFICACIÓN DE RECORDATORIOS (LLAMADA CRÍTICA)
        # Se ejecutan ambas verificaciones para asegurar que no se pierda ninguna notificación.
        # Asegúrate de que estas funciones cierren sus propias conexiones internas.
        verificar_recordatorios_proximos() 
        
        if user_data and user_data['email']:
            verificar_recordatorios_pendientes(session['user_id'], user_data['email'])

        # 4. Parámetros de filtrado
        ver_papelera = request.args.get('papelera', '0')
        tipo_filtro = request.args.get('tipo_filtro', '')
        ver_hechas = request.args.get('ver_hechas', '0')
        buscar = request.args.get('buscar', '') 

        # 5. Construcción de Query Dinámica
        if ver_papelera == '1':
            query = "SELECT * FROM tareas WHERE usuario_id=%s AND eliminado_at IS NOT NULL"
        else:
            query = "SELECT * FROM tareas WHERE usuario_id=%s AND eliminado_at IS NULL"
        
        params = [session['user_id']]
        
        if tipo_filtro:
            query += " AND tipo=%s"
            params.append(tipo_filtro)
        
        if buscar:
            query += " AND (materia LIKE %s OR tema LIKE %s)"
            params.extend([f"%{buscar}%", f"%{buscar}%"])

        if ver_papelera != '1':
            if ver_hechas == '1':
                query += " AND estado='hecha'"
            else:
                query += " AND estado='pendiente'"

        query += " ORDER BY fecha ASC"

        # 6. Ejecución y formateo de datos
        cursor.execute(query, tuple(params))
        tareas = cursor.fetchall()

        for t in tareas:
            # Asignación de color si no existe
            if not t.get('color'):
                t['color'] = string_to_color(t['materia'])
            
            # Formateo de hora (Manejo de timedelta para MySQL)
            if t['hora_entrega']:
                if isinstance(t['hora_entrega'], timedelta):
                    total_seconds = int(t['hora_entrega'].total_seconds())
                    horas = total_seconds // 3600
                    minutos = (total_seconds % 3600) // 60
                    t['hora_entrega'] = f"{horas:02d}:{minutos:02d}"
                else:
                    t['hora_entrega'] = str(t['hora_entrega'])[:5]

        # 7. Renderizado (Se pasan todos los parámetros solicitados)
        return render_template('index.html', 
                               tareas=tareas, 
                               usuario=user_data['usuario'] if user_data else "Usuario", 
                               tipo_filtro=tipo_filtro, 
                               ver_hechas=int(ver_hechas), 
                               buscar=buscar,
                               ver_papelera=int(ver_papelera))
    
    except Exception as e:
        print(f"Error crítico en index: {e}")
        return f"Error interno en la agenda: {e}", 500
        
    finally:
        # ESTE BLOQUE ES VITAL: LIBERA EL POOL DE CONEXIONES
        if cursor:
            cursor.close()
        if db:
            db.close() # OBLIGATORIO para evitar "Pool Exhausted"

@app.route('/ai_analisis')
@login_required
def ai_analisis():
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # 1. Consulta de tareas pendientes
        cursor.execute("""
            SELECT tema, fecha, materia 
            FROM tareas 
            WHERE usuario_id = %s AND estado = 'pendiente' AND eliminado_at IS NULL 
            ORDER BY fecha ASC LIMIT 5
        """, (session['user_id'],))
        
        tareas_pendientes = cursor.fetchall()
        analisis = []
        hoy = datetime.now().date()
        
        # 2. Procesamiento de fechas y tiempos
        for t in tareas_pendientes:
            fecha_t = t['fecha']
            # Conversión de seguridad si la fecha llega como string
            if isinstance(fecha_t, str):
                fecha_t = datetime.strptime(fecha_t, '%Y-%m-%d').date()
            
            dias = (fecha_t - hoy).days
            
            if dias == 0: 
                tiempo = "¡Es hoy! 🚨"
            elif dias == 1: 
                tiempo = "Mañana ⏳"
            elif dias < 0: 
                tiempo = f"Atrasada por {abs(dias)} días ⚠️"
            else: 
                tiempo = f"En {dias} días"
                
            analisis.append({
                "tema": t['tema'],
                "tiempo_restante": tiempo
            })
        
        # 3. Obtención del nombre de usuario
        cursor.execute("SELECT usuario FROM usuarios WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        
        # 4. Respuesta Exitosa
        return jsonify({
            "usuario": user['usuario'] if user else "Maestro",
            "mensaje_intro": "Aquí tienes tu resumen de prioridades:",
            "tareas": analisis
        })

    except Exception as e:
        print(f"Error en IA: {e}")
        return jsonify({"error": "Error interno"}), 500

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

@app.route('/enviar_resumen_semanal')
def resumen_semanal():
    return "Resúmenes enviados"

@app.route('/logros')
@login_required
def logros():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # 1. Datos del usuario
    cursor.execute("SELECT xp, usuario FROM usuarios WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    
    # 2. Conteo de tareas hechas
    cursor.execute("SELECT COUNT(*) as total FROM tareas WHERE usuario_id = %s AND estado = 'hecha'", (session['user_id'],))
    total_hechas = cursor.fetchone()['total'] or 0
    
    # 3. Conteo de tareas en papelera (para ver si es ordenado)
    cursor.execute("SELECT COUNT(*) as total FROM tareas WHERE usuario_id = %s AND eliminado_at IS NOT NULL", (session['user_id'],))
    en_papelera = cursor.fetchone()['total'] or 0
    
    db.close()

    # LISTA DE LOGROS RE-IMPORTANTES
    mis_logros = [
        # --- NIVEL BÁSICO ---
        {"titulo": "Iniciado", "desc": "Completa tu primera tarea.", "meta": 1, "progreso": total_hechas, },
        
        # --- CONSTANCIA ---
        {"titulo": "Soldado de Hierro", "desc": "Completa 25 tareas en total.", "meta": 25, "progreso": total_hechas,},
        {"titulo": "Leyenda Académica", "desc": "Llega a las 100 tareas completadas.", "meta": 100, "progreso": total_hechas,},
        
        # --- PODER (XP) ---
        {"titulo": "Poder Acumulado", "desc": "Alcanza 1,500 de XP.", "meta": 1500, "progreso": user['xp'],},
        {"titulo": "Semidiós", "desc": "Alcanza los 5,000 de XP.", "meta": 5000, "progreso": user['xp'],},
        
        # --- DISCIPLINA ---
        {"titulo": "Productividad Pura", "desc": "Completa 5 tareas de matemáticas.", "meta": 5, "progreso": total_hechas,} # Nota: Aquí podrías filtrar por tema si quieres
    ]
    
    return render_template('logros.html', logros=mis_logros, xp=user['xp'], nombre=user['usuario'])

@app.route('/crear', methods=['GET','POST'])
@login_required
def crear():
    if request.method == 'POST':
        materia = request.form.get('materia')
        tema = request.form.get('tema')
        fecha = request.form.get('fecha')
        hora_entrega = f"{request.form.get('hora_h', '00')}:{request.form.get('hora_m', '00')}:00"
        tipo = request.form.get('tipo')
        importante = 1 if 'importante' in request.form else 0
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO tareas (usuario_id,materia,tema,fecha,hora_entrega,importante,estado,tipo) VALUES(%s,%s,%s,%s,%s,%s,'pendiente',%s)",
            (session['user_id'], materia, tema, fecha, hora_entrega, importante, tipo)
        )
        db.commit()
        db.close()
        flash("Tarea guardada en Agenda Maestra.", "success")
        return redirect(url_for('index'))
    return render_template("crear_editar.html", tarea=None)

@app.route('/vaciar_papelera')
@login_required
def vaciar_papelera():
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Eliminación física (permanente) de lo que esté en la papelera
        cursor.execute("DELETE FROM tareas WHERE usuario_id = %s AND eliminado_at IS NOT NULL", 
                       (session['user_id'],))
        db.commit()
        
        flash("Se han eliminado permanentemente todos los elementos de la papelera.", "success")
    except Exception as e:
        print(f"Error al vaciar papelera: {e}")
        flash("No se pudo vaciar la papelera.", "danger")
    finally:
        if cursor: cursor.close()
        if db: db.close() # Vital para no agotar el pool
        
    return redirect(url_for('index', papelera=1))

@app.route('/restaurar/<int:id>')
@login_required
def restaurar(id):
    db = get_db()
    cursor = db.cursor()
    try:
        # 1. Quitamos la marca de tiempo de 'eliminado_at' para que salga de la papelera
        # 2. Opcionalmente, nos aseguramos de que el estado vuelva a 'pendiente'
        cursor.execute("""
            UPDATE tareas 
            SET eliminado_at = NULL, estado = 'pendiente' 
            WHERE id = %s AND usuario_id = %s
        """, (id, session['user_id']))
        
        db.commit()
        
        if cursor.rowcount == 0:
            flash("No se encontró la tarea o no tienes permiso.", "warning")
        else:
            flash("Tarea restaurada con éxito.", "success")
            
    except Exception as e:
        db.rollback()
        print(f"Error al restaurar: {e}")
        flash("Error en el servidor al intentar restaurar.", "danger")
    finally:
        cursor.close()
        db.close()
    
    # Redirigimos a la agenda normal para ver el cambio
    return redirect(url_for('index'))

@app.route('/completar/<int:id>')
@login_required
def completar(id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # 1. Obtener la tarea y validar que pertenezca al usuario logueado
        # Obtenemos también el XP actual del usuario para calcular si sube de nivel
        cursor.execute("""
            SELECT t.*, u.email, u.usuario, u.xp as xp_actual FROM tareas t 
            JOIN usuarios u ON t.usuario_id = u.id 
            WHERE t.id=%s AND t.usuario_id=%s
        """, (id, session['user_id']))
        data = cursor.fetchone()
        
        if data:
            # 2. Lógica de cambio de estado y puntos de XP
            nuevo_estado = 'pendiente' if data['estado'] == 'hecha' else 'hecha'
            puntos = 50 if nuevo_estado == 'hecha' else -50
            
            # --- LÓGICA DE NIVEL (EJEMPLO) ---
            # Calculamos niveles basados en rangos de 500 XP
            xp_antes = data['xp_actual']
            xp_despues = max(0, xp_antes + puntos)
            nivel_antes = (xp_antes // 500) + 1
            nuevo_nivel = (xp_despues // 500) + 1
            subio_de_nivel = nuevo_nivel > nivel_antes
            # ---------------------------------

            # 3. Ejecutar actualizaciones dentro de una transacción
            cursor.execute("UPDATE tareas SET estado=%s WHERE id=%s", (nuevo_estado, id))
            cursor.execute("UPDATE usuarios SET xp=%s WHERE id=%s", (xp_despues, session['user_id']))
            
            # Confirmar cambios en la base de datos antes de disparar correos
            db.commit()

            # 4. Notificaciones y Logros
            if nuevo_estado == 'hecha':
                try:
                    # Notificación estándar de tarea completada
                    if data.get('email'):
                        enviar_correo_notificacion(data['email'], data['usuario'], data['tema'], "COMPLETADA")
                    
                    # LLAMADA CRÍTICA: Si subió de nivel, disparamos el correo de logro
                    if subio_de_nivel:
                        notificar_logro(session['user_id'], "Nivel", nuevo_nivel)
                        flash(f"¡Felicidades! Alcanzaste el nivel {nuevo_nivel} 🏆", "success")
                    else:
                        flash(f"Tarea completada. +50 XP", "info")
                
                except Exception as mail_error:
                    # Si falla el mail, no queremos que se rompa la app
                    print(f"Error enviando notificaciones: {mail_error}")
            else:
                flash("Tarea marcada como pendiente.", "warning")

    except Exception as e:
        # Si algo falla en la DB, deshacemos los cambios para evitar datos corruptos
        if db:
            db.rollback()
        print(f"Error crítico en completar: {e}")
        flash("Ocurrió un error al actualizar la tarea.", "danger")
    finally:
        # Cerramos siempre las conexiones para no saturar el servidor MySQL
        if cursor:
            cursor.close()
        if db:
            db.close()
        
    return redirect(request.referrer or url_for('index'))

@app.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    db = None # Inicializamos para evitar errores en el finally
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Ejecutamos la lógica
        cursor.execute("UPDATE tareas SET eliminado_at=NOW() WHERE id=%s AND usuario_id=%s", 
                       (id, session['user_id']))
        db.commit()
        
        flash("Tarea enviada a la papelera (se borrará en 2 días).", "info")
        return redirect(url_for('index'))

    except Exception as e:
        print(f"Error al eliminar: {e}")
        flash("Ocurrió un error al intentar eliminar.", "danger")
        return redirect(url_for('index'))

    finally:
        # Esto es lo que evita el "Pool Exhausted"
        if cursor:
            cursor.close()
        if db:
            db.close()

@app.route('/perfil')
@login_required
def perfil():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    
    edad = None
    if user['cumpleanos']:
        today = date.today()
        cumple = user['cumpleanos'] # Asumiendo que es objeto date o datetime
        edad = today.year - cumple.year - ((today.month, today.day) < (cumple.month, cumple.day))

    racha = user.get('racha_dias', 0) 

    xp = user['xp']
    nivel = (xp // 100) + 1
    xp_barra = xp % 100
    rangos = ["Novato", "Aprendiz", "Oficial", "Maestro", "Leyenda"]
    rango = rangos[min(nivel // 5, len(rangos)-1)]

    db.close()
    return render_template('perfil.html', user=user, nivel=nivel, xp_barra=xp_barra, rango=rango, edad=edad, racha=racha)

@app.route('/calendario')
@login_required
def calendario():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, materia, tema, fecha, tipo FROM tareas WHERE usuario_id=%s AND eliminado_at IS NULL", (session['user_id'],))
    tareas = cursor.fetchall()
    db.close()
    eventos = [{'title': f"[{t['materia']}] {t['tema']}", 'start': str(t['fecha']), 'color': "#38bdf8" if t['tipo'] == 'tarea' else "#ef4444", 'url': url_for('editar', id=t['id'])} for t in tareas]
    return render_template("calendario.html", eventos=eventos)

@app.route('/estadisticas')
@login_required
def estadisticas():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) total FROM tareas WHERE usuario_id=%s AND eliminado_at IS NULL", (session['user_id'],))
    total = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) hechas FROM tareas WHERE usuario_id=%s AND estado='hecha' AND eliminado_at IS NULL", (session['user_id'],))
    hechas = cursor.fetchone()['hechas']
    cursor.execute("SELECT materia, COUNT(*) as cant FROM tareas WHERE usuario_id=%s AND eliminado_at IS NULL GROUP BY materia", (session['user_id'],))
    materias_resumen = cursor.fetchall()
    db.close()
    return render_template("estadisticas.html", total=total, hechas=hechas, pendientes=total-hechas,
                           labels_materias=[m['materia'] for m in materias_resumen],
                           values_materias=[m['cant'] for m in materias_resumen])

@app.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada en Agenda Maestra.", "info")
    return redirect(url_for('login'))

@app.route('/backup')
@login_required
def backup():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tareas WHERE usuario_id=%s", (session['user_id'],))
        tareas = cursor.fetchall()
        db.close()
        return Response(json.dumps(tareas, default=str), mimetype='application/json',
                        headers={'Content-Disposition': 'attachment;filename=respaldo_agenda_maestra.json'})
    except Exception as e:
        flash("Error al generar el respaldo.", "danger")
        return redirect(url_for('index'))

@app.route('/editar_perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    if request.method == 'POST':
        email = request.form.get('email')
        cumpleanos = request.form.get('cumpleanos')
        foto_archivo = request.files.get('foto_perfil')
        foto_base64 = None
        if foto_archivo and foto_archivo.filename != '':
            fileread = foto_archivo.read()
            encoded = base64.b64encode(fileread).decode('utf-8')
            foto_base64 = f"data:{foto_archivo.mimetype};base64,{encoded}"
            cursor.execute("UPDATE usuarios SET email=%s, cumpleanos=%s, foto_perfil=%s WHERE id=%s", (email, cumpleanos, foto_base64, session['user_id']))
        else:
            cursor.execute("UPDATE usuarios SET email=%s, cumpleanos=%s WHERE id=%s", (email, cumpleanos, session['user_id']))
        db.commit()
        db.close()
        flash("Perfil actualizado.", "success")
        return redirect(url_for('perfil'))
    cursor.execute("SELECT * FROM usuarios WHERE id=%s", (session['user_id'],))
    user = cursor.fetchone()
    db.close()
    return render_template("editar_perfil.html", user=user)

@app.route('/editar/<int:id>', methods=['GET','POST'])
@login_required
def editar(id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tareas WHERE id=%s AND usuario_id=%s", (id, session['user_id']))
    tarea = cursor.fetchone()
    if not tarea:
        flash("Acceso denegado.", "danger")
        db.close()
        return redirect(url_for('index'))
    if request.method == 'POST':
        materia = request.form.get('materia')
        tema = request.form.get('tema')
        fecha = request.form.get('fecha')
        hora_entrega = f"{request.form.get('hora_h', '00')}:{request.form.get('hora_m', '00')}:00"
        tipo = request.form.get('tipo')
        importante = 1 if 'importante' in request.form else 0
        cursor.execute(
            "UPDATE tareas SET materia=%s,tema=%s,fecha=%s,hora_entrega=%s,importante=%s,tipo=%s WHERE id=%s AND usuario_id=%s",
            (materia, tema, fecha, hora_entrega, importante, tipo, id, session['user_id'])
        )
        db.commit()
        db.close()
        flash("Tarea actualizada.", "success")
        return redirect(url_for('index'))
    db.close()
    return render_template("crear_editar.html", tarea=tarea)

if __name__ == '__main__':
    app.run(debug=True)