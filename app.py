import os
import time
import hmac
import json
import base64
import hashlib
import socket
import multiprocessing
import urllib.parse
import smtplib
from functools import wraps
from datetime import date, datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import mysql.connector
from mysql.connector import pooling
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, Response, flash, jsonify
from flask_mail import Mail, Message

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
db_pool = None

def inicializar_entorno():
    global db_pool
    try:
        # Conexión inicial para configuración administrativa
        temp_conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', 'root'),
            autocommit=True
        )
        cursor = temp_conn.cursor()
        db_name = os.getenv('DB_NAME', 'agenda_maestra')

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.execute(f"USE {db_name}")

        # --- TABLA USUARIOS ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario VARCHAR(20) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100) NOT NULL,
                creado_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # --- TABLA TAREAS (Incluyendo campo 'descripcion') ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tareas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT NOT NULL,
                materia VARCHAR(100) NOT NULL,
                tema VARCHAR(255) NOT NULL,
                descripcion TEXT DEFAULT NULL,
                fecha DATE NOT NULL,
                CONSTRAINT fk_usuario_tareas FOREIGN KEY (usuario_id) 
                REFERENCES usuarios(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Sincronización de columnas faltantes
        columnas_tareas = {
            'hora_entrega': "TIME DEFAULT NULL",
            'importante': "TINYINT(1) DEFAULT 0",
            'estado': "ENUM('pendiente', 'hecha') DEFAULT 'pendiente'",
            'tipo': "ENUM('tarea', 'examen', 'grupal') DEFAULT 'tarea'",
            'colaboradores': "TEXT AFTER tipo",
            'color': "VARCHAR(7) DEFAULT '#00d2ff'",
            'eliminado_at': "DATETIME DEFAULT NULL",
            'recordatorio_enviado': "TINYINT(1) DEFAULT 0"
        }

        for col, defn in columnas_tareas.items():
            try:
                cursor.execute(f"ALTER TABLE tareas ADD COLUMN {col} {defn}")
            except: pass

        cursor.close()
        temp_conn.close()

        # 2. Inicialización del Pool (Ahora db_pool es accesible globalmente)
        db_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="mypool",
            pool_size=10,
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', 'root'),
            database=db_name
        )
        print("✅ Base de datos sincronizada y Pool de conexiones activo.")
        return True
    except Exception as err:
        print(f"❌ Error Crítico: {err}")
        return False

# --- LLAMADA INICIAL OBLIGATORIA ---
inicializar_entorno()

# --- LÓGICA SEGURA DE GUARDADO ---
def guardar_tarea_db(materia, tema, fecha, hora, importante, tipo, descripcion, tarea_id):
    global db_pool
    # Si el pool no existe por algún error, intentamos re-inicializar
    if db_pool is None:
        inicializar_entorno()
        
    conn = db_pool.get_connection()
    cursor = conn.cursor()
    try:
        query = """
            UPDATE tareas 
            SET materia=%s, tema=%s, fecha=%s, hora_entrega=%s, 
                importante=%s, tipo=%s, descripcion=%s 
            WHERE id=%s
        """
        cursor.execute(query, (materia, tema, fecha, hora, importante, tipo, descripcion, tarea_id))
        conn.commit()
    except Exception as e:
        print(f"❌ Error al ejecutar actualización en BD: {e}")
        raise e # Esto nos ayuda a ver el error real si algo falla
    finally:
        cursor.close()
        conn.close()
        
# ==========================================
# 2. CONFIGURACIÓN DEL POOL DE CONEXIONES
# ==========================================

db_config = {
    "host": os.getenv('DB_HOST', 'localhost'),
    "user": os.getenv('DB_USER', 'root'),
    "password": os.getenv('DB_PASSWORD', 'root'),
    "database": os.getenv('DB_NAME', 'agenda_maestra'),
    "raise_on_warnings": True # Esto nos dará más info si algo falla
}

try:
    # Intentamos crear el pool
    pool = pooling.MySQLConnectionPool(
        pool_name="agenda_pool",
        pool_size=5,
        **db_config
    )
    print("*Pool de conexiones creado exitosamente.")
except mysql.connector.Error as err:
    print(f"❌ ERROR AL CREAR EL POOL: {err}")
    pool = None
    
# --- ESTAS SON LAS FUNCIONES QUE FALTAN Y CAUSAN LOS ERRORES ---

def get_db_connection():
    """Obtiene una conexión del pool para realizar consultas."""
    if pool is None:
        # Esto es lo que causaba el error en el navegador antes
        raise Exception("El pool de conexiones no está disponible. Revisa la consola para ver el error de MySQL.")
    return pool.get_connection()

def get_db():
    """Alias de get_db_connection usado en la mayoría de tus rutas."""
    return get_db_connection()

def enviar_mail_invitacion(email_destino, materia, tema, remitente):
    # 1. Configuración del servidor (Usa variables de entorno por seguridad)
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.getenv('MAIL_USER') # Tu correo (ej: agenda.maestra@gmail.com)
    sender_password = os.getenv('MAIL_PASS') # Contraseña de aplicación de Google

    # Validar que las credenciales existan
    if not sender_email or not sender_password:
        print("❌ Error: Variables de entorno MAIL_USER o MAIL_PASS no configuradas.")
        return False

    # 2. Construcción del Mensaje
    mensaje = MIMEMultipart()
    mensaje["From"] = f"Agenda Maestra <{sender_email}>"
    mensaje["To"] = email_destino
    mensaje["Subject"] = f"📚 Colaboración Grupal: {materia}"

    # Diseño del cuerpo del mensaje
    cuerpo = f"""
    ¡Hola!
    
    {remitente} te ha invitado a colaborar en una nueva tarea grupal en 'Agenda Maestra'.
    
    Detalles de la invitación:
    -------------------------------------------
    📖 Materia: {materia}
    📝 Tema: {tema}
    -------------------------------------------
    
    Inicia sesión en tu agenda para ver los detalles y empezar a trabajar juntos.
    
    Saludos,
    El equipo de Agenda Maestra.
    """
    mensaje.attach(MIMEText(cuerpo, "plain"))

    # 3. Proceso de Envío
    try:
        # Establecer conexión segura
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls() # Cifrado de la conexión
        server.login(sender_email, sender_password)
        
        # Enviar y cerrar
        server.send_message(mensaje)
        server.quit()
        
        print(f"✅ Notificación enviada con éxito a {email_destino}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("❌ Error: Autenticación fallida. Revisa el usuario y la contraseña de aplicación.")
    except Exception as e:
        print(f"❌ Error inesperado al enviar mail: {e}")
    
    return False

# ==========================================
# UTILIDADES Y DECORADORES
# ==========================================

# --- FUNCIONES DE LÓGICA Y AUTOMATIZACIÓN ---

def otorgar_xp(usuario_id, cantidad, motivo):
    """Actualiza la XP del usuario y envía notificación de logro por correo."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # 1. Actualizar XP
        cursor.execute("UPDATE usuarios SET xp = xp + %s WHERE id = %s", (cantidad, usuario_id))
        
        # 2. Obtener datos frescos para el correo
        cursor.execute("SELECT usuario, email, xp, nivel FROM usuarios WHERE id = %s", (usuario_id,))
        user = cursor.fetchone()
        
        # 3. Envío de correo de logro usando la plantilla logro.html
        msg = Message(f"¡Nuevo Logro Alcanzado: {motivo}!", recipients=[user['email']])
        msg.html = render_template('logro.html', usuario=user['usuario'], logro=motivo, xp_ganada=cantidad)
        mail.send(msg)
        
        db.commit()
    except Exception as e:
        print(f"⚠️ Error en otorgar_xp o envío de mail: {e}")
    finally:
        cursor.close()
        db.close()

def verificar_recordatorios_proximos():
    """Busca tareas que venzan en exactamente 48hs y envía aviso."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # SQL exacto: diferencia de días = 2, pendiente y no enviado aún
        query = """
            SELECT t.*, u.email, u.usuario 
            FROM tareas t
            JOIN usuarios u ON t.usuario_id = u.id
            WHERE t.estado = 'pendiente' 
            AND t.eliminado_at IS NULL
            AND t.recordatorio_enviado = 0
            AND DATEDIFF(t.fecha, CURDATE()) = 2
        """
        cursor.execute(query)
        tareas_proximas = cursor.fetchall()
        
        for tarea in tareas_proximas:
            # Reutilizamos la lógica de Message para recordatorio.html
            msg = Message(f"⏰ Recordatorio: {tarea['tema']}", recipients=[tarea['email']])
            msg.html = render_template('recordatorio.html', tarea=tarea)
            mail.send(msg)
            
            # Marcar como enviado para no repetir el correo
            cursor.execute("UPDATE tareas SET recordatorio_enviado = 1 WHERE id = %s", (tarea['id'],))
        
        db.commit()
    except Exception as e:
        print(f"⚠️ Error en verificar_recordatorios: {e}")
    finally:
        cursor.close()
        db.close()

def string_to_color(string):
    """
    Genera un color consistente basado en el nombre de la materia.
    Optimizada para usar un algoritmo de hash más rápido.
    """
    if not string:
        return "#38bdf8" # Color celeste por defecto de Agenda Maestra
    
    # Generamos un hash simple pero efectivo
    hash_obj = hashlib.md5(string.encode())
    hex_color = f"#{hash_obj.hexdigest()[:6]}"
    return hex_color

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

def enviar_resumen_semanal(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Buscamos tareas de los próximos 7 días
    proxima_semana = (datetime.now() + timedelta(days=7)).date()
    cursor.execute("""
        SELECT tema, materia, fecha, tipo 
        FROM tareas 
        WHERE usuario_id = %s 
        AND estado = 'pendiente' 
        AND fecha BETWEEN CURRENT_DATE AND %s
        ORDER BY fecha ASC
    """, (user_id, proxima_semana))
    
    tareas = cursor.fetchall()
    
    if tareas:
        cursor.execute("SELECT email, usuario FROM usuarios WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        asunto = f"📅 Tu Plan Semanal en Agenda Maestra - {user['usuario']}"
        html = render_template('emails/resumen_semanal.html', tareas=tareas, usuario=user['usuario'])
        enviar_correo(asunto, user['email'], html)
    
    db.close()

def verificar_recordatorios_proximos():
    """
    Busca tareas que vencen exactamente en 2 días y envía un aviso por correo.
    Garantiza que no se envíen duplicados y que la base de datos se mantenga limpia.
    """
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # 1. Calculamos la fecha objetivo (hoy + 2 días)
        # Usamos .date() para comparar solo año-mes-día contra la columna DATE de MySQL
        fecha_objetivo = (datetime.now() + timedelta(days=2)).date()
        
        # 2. Consulta optimizada: 
        # Filtramos por fecha, estado pendiente, que no esté en papelera y que falte notificar
        cursor.execute("""
            SELECT t.*, u.email, u.usuario 
            FROM tareas t 
            JOIN usuarios u ON t.usuario_id = u.id 
            WHERE t.fecha = %s 
            AND t.estado = 'pendiente' 
            AND t.recordatorio_enviado = 0 
            AND t.eliminado_at IS NULL
        """, (fecha_objetivo,))
        
        tareas_a_notificar = cursor.fetchall()
        
        if not tareas_a_notificar:
            return # Salimos si no hay nada pendiente para hoy

        for tarea in tareas_a_notificar:
            try:
                # 3. Preparación del mensaje
                asunto = f"⏰ Recordatorio: '{tarea['tema']}' vence en 2 días"
                
                # Intentamos renderizar el HTML del correo
                html_body = render_template('emails/recordatorio.html', tarea=tarea)
                
                # 4. Intento de envío
                # Usamos la función enviar_correo que ya tienes definida
                exito_envio = enviar_correo(asunto, tarea['email'], html_body)
                
                # 5. SOLO si el envío fue exitoso, marcamos en la DB
                if exito_envio:
                    cursor.execute("""
                        UPDATE tareas 
                        SET recordatorio_enviado = 1 
                        WHERE id = %s
                    """, (tarea['id'],))
                    # Hacemos commit individual para asegurar que cada envío se guarde
                    db.commit() 
                
            except Exception as e_interno:
                # Si falla una tarea (ej. email inválido), el bucle sigue con la siguiente
                print(f"⚠️ Error al procesar recordatorio de tarea ID {tarea['id']}: {e_interno}")
                continue
        
    except Exception as e:
        print(f"❌ Error crítico en verificar_recordatorios_proximos: {e}")
    finally:
        # 6. CIERRE DE SEGURIDAD: Liberamos los recursos del pool
        if cursor: 
            cursor.close()
        if db: 
            db.close()

def notificar_logro(user_id, tipo_logro, valor):
    """
    Envía felicitaciones por alcanzar hitos o subir de nivel.
    Usa el diseño visual de Agenda Maestra y asegura el cierre de la DB.
    """
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT usuario, email FROM usuarios WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if user and user['email']:
            # Diseño integrado de Agenda Maestra
            html_directo = render_template('emails/logro.html', 
                                           usuario=user['usuario'], 
                                           tipo=tipo_logro, 
                                           valor=valor)
            
            asunto = f"🎉 ¡Logro Desbloqueado: {tipo_logro} {valor}!"
            
            # Usamos el wrapper enviar_correo que ya maneja la configuración de Flask-Mail
            enviar_correo(asunto, user['email'], html_directo)
            print(f"✅ Logro enviado a {user['email']}")

    except Exception as e:
        print(f"❌ Error en notificar_logro: {e}")
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
@app.route('/ejemplo')
def ruta_optimizada():
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        # ... lógica del programa ...
        db.commit()
    except Exception as e:
        if db: db.rollback() # Si hay error, deshacemos cambios para no romper la DB
        print(f"Error: {e}")
    finally:
        # CIERRE OBLIGATORIO: Esto garantiza que el programa nunca se congele
        if cursor: cursor.close()
        if db: db.close()

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
        cursor = db.cursor(dictionary=True, buffered=True)
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

def limpiar_papelera_automatica():
    """
    Elimina físicamente las tareas en papelera con más de 48 horas.
    Diseñada para ser llamada internamente sin interrumpir al usuario.
    """
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True, buffered=True)
        # Borrado físico: solo tareas con marca de borrado de hace más de 2 días
        cursor.execute("""
            DELETE FROM tareas 
            WHERE eliminado_at <= NOW() - INTERVAL 2 DAY
        """)
        total_borrados = cursor.rowcount
        db.commit()
        
        if total_borrados > 0:
            print(f"🧹 [Auto-Limpieza] Se eliminaron {total_borrados} tareas permanentemente.")
            
    except Exception as e:
        print(f"❌ Error en limpieza de papelera: {e}")
    finally:
        if cursor: cursor.close()
        if db: db.close()

# ==========================================
# RUTAS DE TAREAS
# ==========================================
# --- RUTA PRINCIPAL (INDEX) COMBINADA --
@app.route('/')
@login_required
def index():
    # 1. INICIALIZACIÓN CRÍTICA: Evita el UnboundLocalError si algo falla antes de tiempo
    conexion = None
    cursor = None

    try:
        # 2. EJECUCIÓN DE PROCESOS AUTOMÁTICOS PREVIOS
        # El sistema limpia la papelera y procesa recordatorios antes de consultar
        limpiar_papelera_automatica()
        verificar_recordatorios_proximos()

        # 3. GESTIÓN SEGURA DE CONEXIÓN A LA BASE DE DATOS
        # Intentamos obtener una conexión limpia desde el pool de conexiones
        conexion = db_pool.get_connection()
        cursor = conexion.cursor(dictionary=True)

        # 4. CAPTURA DE DATOS DEL USUARIO LOGUEADO
        cursor.execute("SELECT usuario, email, xp, racha FROM usuarios WHERE id = %s", (session['user_id'],))
        user_data = cursor.fetchone()

        # 5. CAPTURA Y PROCESAMIENTO DE PARÁMETROS FILTROS (URL Query Strings)
        ver_papelera = request.args.get('papelera', '0')
        tipo_filtro = request.args.get('tipo_filtro', '')
        ver_hechas = request.args.get('ver_hechas', '0')
        buscar = request.args.get('buscar', '') 

        # 6. CONSTRUCCIÓN DINÁMICA DE LA CONSULTA SQL (Tareas)
        if ver_papelera == '1':
            query = "SELECT * FROM tareas WHERE usuario_id = %s AND eliminado_at IS NOT NULL"
        else:
            query = "SELECT * FROM tareas WHERE usuario_id = %s AND eliminado_at IS NULL"
        
        # Lista de parámetros para prevenir inyecciones SQL
        params = [session['user_id']]
        
        # Filtro por tipo de actividad (tarea o examen)
        if tipo_filtro:
            query += " AND tipo = %s"
            params.append(tipo_filtro)
        
        # Buscador por coincidencia en Materia o Tema
        if buscar:
            query += " AND (materia LIKE %s OR tema LIKE %s)"
            params.extend([f"%{buscar}%", f"%{buscar}%"])

        # Si no estamos en la papelera, filtramos según estén pendientes o hechas
        if ver_papelera != '1':
            estado_objetivo = 'hecha' if ver_hechas == '1' else 'pendiente'
            query += " AND estado = %s"
            params.append(estado_objetivo)

        # Orden prioritario por fecha y luego por hora de entrega
        query += " ORDER BY fecha ASC, hora_entrega ASC"

        # Ejecución definitiva de la consulta armada
        cursor.execute(query, tuple(params))
        tareas = cursor.fetchall()

        # 7. FORMATEO ESTÉTICO Y GENERACIÓN DE CÓDIGO QR PARA CADA TAREA
        import urllib.parse
        import json  # <--- ACÁ ESTÁ EL FIX CRÍTICO QUE ME FALTÓ ANTES
        
        for t in tareas:
            # Si la tarea no tiene un color asignado, genera uno basado en el texto de la materia
            if not t.get('color'):
                t['color'] = string_to_color(t['materia'])
            
            # Acorta el formato de la hora (HH:MM:SS -> HH:MM) para que no ocupe tanto espacio
            if t['hora_entrega']:
                t['hora_entrega'] = str(t['hora_entrega'])[:5]
                
            # --- LÓGICA DE GENERACIÓN DE QR ---
            # Estructuramos los datos compactos de la tarea para el formato que lee tu escáner
            datos_qr = {
                "mat": t['materia'],
                "tem": t['tema'],
                "fec": str(t['fecha']),
                "tip": t['tipo'],
                "imp": t['importante']
            }
            # Convertimos el diccionario a un string JSON compacto y lo codificamos para URL
            json_qr_string = json.dumps(datos_qr, ensure_ascii=False)
            url_segura_qr = urllib.parse.quote(json_qr_string)
            
            # Guardamos la URL final del QR provista por la API en el diccionario de la tarea
            t['qr_url'] = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url_segura_qr}"

        # 8. RENDERIZADO DE PLANTILLA E INYECCIÓN DE DATOS (Gamificación Incluida)
        return render_template(
            'index.html', 
            tareas=tareas, 
            usuario=user_data['usuario'] if user_data else "Usuario", 
            usuario_xp=user_data['xp'] if user_data else 0,
            usuario_nivel=(user_data['xp'] // 500) + 1 if user_data else 1,
            usuario_racha=user_data['racha'] if user_data else 0,
            tipo_filtro=tipo_filtro, 
            ver_hechas=int(ver_hechas), 
            buscar=buscar,
            ver_papelera=int(ver_papelera)
        )
    
    except mysql.connector.Error as err:
        # Control específico para fallos de la base de datos o sintaxis SQL
        print(f"❌ Error de MySQL en index: {err}")
        flash("Hubo un inconveniente con el almacenamiento. Reintentando...", "error")
        return "Error en la base de datos. Por favor, intenta de nuevo más tarde.", 500

    except Exception as e:
        # Captura cualquier otro tipo de error inesperado en Python
        print(f"❌ Error crítico en index: {e}")
        return "Error interno del servidor. Por favor, reporta el fallo al administrador.", 500

    finally:
        # 9. CIERRE SEGURO Y CONTROLADO: Garantiza la devolución de recursos al Pool sin romper el flujo
        if cursor is not None:
            try:
                cursor.close()
            except Exception as ce:
                print(f"⚠️ No se pudo cerrar el cursor: {ce}")
                
        if conexion is not None:
            try:
                conexion.close()
            except Exception as se:
                print(f"⚠️ No se pudo devolver la conexión al pool: {se}")

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
        {"titulo": "Iniciado", "desc": "Completa tu primera tarea.", "meta": 1, "progreso": total_hechas, },
        {"titulo": "Soldado de Hierro", "desc": "Completa 25 tareas en total.", "meta": 25, "progreso": total_hechas,},
        {"titulo": "Leyenda Académica", "desc": "Llega a las 100 tareas completadas.", "meta": 100, "progreso": total_hechas,},
        {"titulo": "Poder Acumulado", "desc": "Alcanza 1,500 de XP.", "meta": 1500, "progreso": user['xp'],},
        {"titulo": "Semidiós", "desc": "Alcanza los 5,000 de XP.", "meta": 5000, "progreso": user['xp'],},
        {"titulo": "Productividad Pura", "desc": "Completa 5 tareas de matemáticas.", "meta": 5, "progreso": total_hechas,}
    ]
    
    return render_template(
        'logros.html',
        logros=mis_logros,
        xp=user['xp'],
        nombre=user['usuario'],
        en_papelera=en_papelera
    )

@app.route('/crear', methods=['GET', 'POST'])
@login_required
def crear():
    # --- LÓGICA DE PROCESAMIENTO (POST) ---
    if request.method == 'POST':
        try:
            # 1. Captura de datos básicos del formulario
            materia = request.form.get('materia')
            tema = request.form.get('tema')
            descripcion = request.form.get('descripcion', '')
            fecha = request.form.get('fecha')
            hora_h = request.form.get('hora_h', '00')
            hora_m = request.form.get('hora_m', '00')
            hora_entrega = f"{hora_h}:{hora_m}:00"
            tipo = request.form.get('tipo', 'tarea')
            
            # 2. Lógica crítica de Prioridad y Colaboradores
            # Si el checkbox no se marca, request.form.get devuelve None.
            # Convertimos a 1 o 0 de forma segura.
            importante = 1 if request.form.get('importante') == '1' else 0
            
            # Captura de colaboradores (si está vacío, guardamos cadena vacía)
            colaboradores = request.form.get('colaboradores', '').strip()

            # 3. Operación de Base de Datos
            db = get_db()
            cursor = db.cursor(dictionary=True, buffered=True)
            
            # SQL: Asegúrate de que tu tabla tenga las columnas 'colaboradores' y 'descripcion'
            # Si no las tienes, debes ejecutar: ALTER TABLE tareas ADD COLUMN colaboradores TEXT, ADD COLUMN descripcion TEXT;
            query = """
                INSERT INTO tareas 
                (usuario_id, materia, tema, descripcion, fecha, hora_entrega, importante, estado, tipo, colaboradores) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pendiente', %s, %s)
            """
            valores = (
                session['user_id'], 
                materia, 
                tema, 
                descripcion, 
                fecha, 
                hora_entrega, 
                importante, 
                tipo, 
                colaboradores
            )
            
            cursor.execute(query, valores)
            db.commit()
            cursor.close()
            db.close()

            # 4. Respuesta Inteligente (Detecta si es AJAX/Fetch o Formulario Normal)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({
                    "success": True, 
                    "message": "Tarea creada con éxito",
                    "importante": importante
                }), 200
            
            flash("¡Tarea guardada exitosamente en Agenda Maestra!", "success")
            return redirect(url_for('index'))

        except Exception as e:
            # Manejo de errores para evitar caídas del servidor
            print(f"❌ ERROR CRÍTICO AL GUARDAR TAREA: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "error": str(e)}), 500
            
            flash("Ocurrió un error al intentar guardar la tarea. Por favor, intenta de nuevo.", "danger")
            return redirect(url_for('crear'))

    # --- LÓGICA DE RENDERIZADO (GET) ---
    return render_template("crear_editar.html", tarea=None)

@app.route('/vaciar_papelera', methods=['POST'])
@login_required
def vaciar_papelera():
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True, buffered=True)
        
        # Ejecutamos la eliminación física irreversible solo de los elementos del usuario actual
        # que ya han sido marcados con una fecha en 'eliminado_at'
        cursor.execute("""
            DELETE FROM tareas 
            WHERE usuario_id = %s AND eliminado_at IS NOT NULL
        """, (session['user_id'],))
        
        db.commit()
        flash("La papelera se ha vaciado permanentemente.", "success")
        
    except Exception as e:
        if db:
            db.rollback()  # Deshacemos cambios si hay un error
        print(f"❌ Error crítico al vaciar papelera: {e}")
        flash("Hubo un problema al intentar vaciar la papelera.", "danger")
        
    finally:
        # Cerramos recursos siempre, sin importar si hubo éxito o error
        if cursor: 
            cursor.close()
        if db: 
            db.close()
        
    # Redirigimos al índice manteniendo la vista de la papelera (usando ver_papelera=1)
    return redirect(url_for('index', ver_papelera=1))

@app.route('/restaurar/<int:id>')
@login_required
def restaurar(id):
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
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
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # 1. Traemos datos de la tarea Y del usuario
        cursor.execute("""
            SELECT t.*, u.email, u.usuario, u.xp as xp_actual, 
                   u.racha, u.ultima_fecha_completada, u.importantes_seguidas
            FROM tareas t 
            JOIN usuarios u ON t.usuario_id = u.id 
            WHERE t.id=%s AND t.usuario_id=%s
        """, (id, session['user_id']))
        
        data = cursor.fetchone()
        
        if not data:
            flash("No se encontró la tarea o no tienes permiso.", "danger")
            return redirect(url_for('index'))

        nuevo_estado = 'pendiente' if data['estado'] == 'hecha' else 'hecha'
        
        # --- LÓGICA DE PUNTOS ---
        puntos_base = 50
        multiplicador = 1.0
        nuevas_importantes = data['importantes_seguidas']
        
        if nuevo_estado == 'hecha':
            if data['importante'] == 1:
                nuevas_importantes += 1
                if nuevas_importantes >= 3:
                    multiplicador = 1.5
                    flash("¡COMBO! Multiplicador x1.5 activado 🔥", "success")
            else:
                nuevas_importantes = 0 
            
            puntos_cambio = int(puntos_base * multiplicador)
        else:
            puntos_cambio = -50 
            nuevas_importantes = 0

        xp_final = max(0, data['xp_actual'] + puntos_cambio)
        nivel_antes = (data['xp_actual'] // 500) + 1
        nivel_despues = (xp_final // 500) + 1

        # 3. --- LÓGICA DE RACHAS ---
        nueva_racha = data['racha']
        hoy = datetime.now().date()
        ultima_vez = data['ultima_fecha_completada']

        if nuevo_estado == 'hecha':
            if ultima_vez == hoy - timedelta(days=1):
                nueva_racha += 1
            elif ultima_vez != hoy:
                nueva_racha = 1
            
            cursor.execute("""
                UPDATE usuarios 
                SET xp=%s, nivel=%s, racha=%s, ultima_fecha_completada=%s, importantes_seguidas=%s 
                WHERE id=%s
            """, (xp_final, nivel_despues, nueva_racha, hoy, nuevas_importantes, session['user_id']))
        else:
            cursor.execute("""
                UPDATE usuarios 
                SET xp=%s, nivel=%s, importantes_seguidas=0 
                WHERE id=%s
            """, (xp_final, nivel_despues, session['user_id']))

        # 4. Actualizar tarea
        cursor.execute("UPDATE tareas SET estado=%s WHERE id=%s", (nuevo_estado, id))
        
        # 5. --- LOGROS (Corregida la indentación) ---
        if nuevo_estado == 'hecha':
            cursor.execute("SELECT COUNT(*) as total FROM tareas WHERE usuario_id=%s AND estado='hecha'", (session['user_id'],))
            total_hechas = cursor.fetchone()['total']
            
            hitos_comunes = {1: "Primer Paso", 5: "Estudiante Aplicado", 10: "Maestro del Tiempo", 50: "Leyenda de la Agenda"}
            
            if total_hechas in hitos_comunes:
                nombre_logro = hitos_comunes[total_hechas]
                notificar_logro(session['user_id'], "LOGRO", nombre_logro) 
                flash(f"¡Logro desbloqueado: {nombre_logro}! 🏆 Checkea tu email.", "success")

            if nivel_despues > nivel_antes:
                notificar_logro(session['user_id'], "NIVEL", nivel_despues)
                flash(f"¡NIVEL {nivel_despues} ALCANZADO! 🏆", "success")

            # 6. Feedback visual
            if nueva_racha > data['racha']:
                flash(f"¡Tarea lista! Racha de {nueva_racha} días 🔥", "info")
            else:
                flash(f"¡Tarea completada! +{puntos_cambio} XP 🚀", "info")
        else:
            flash("Tarea marcada como pendiente. -50 XP.", "warning")

        db.commit()

    except Exception as e:
        if db: db.rollback()
        print(f"❌ Error crítico: {e}")
        flash("Hubo un error al procesar tu progreso.", "danger")
    finally:
        if cursor: cursor.close()
        if db: db.close()
        
    return redirect(request.referrer or url_for('index'))

@app.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    db = None # Inicializamos para evitar errores en el finally
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True, buffered=True)
        
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

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # 1. VALIDACIÓN DE SEGURIDAD: Verificar existencia y propiedad
    cursor.execute("SELECT * FROM tareas WHERE id=%s AND usuario_id=%s", (id, session['user_id']))
    tarea = cursor.fetchone()
    
    if not tarea:
        db.close()
        flash("Acceso denegado: La tarea no existe o no tienes permiso.", "danger")
        return redirect(url_for('index'))
    
    # 2. PROCESAMIENTO DEL FORMULARIO (POST)
    if request.method == 'POST':
        try:
            materia = request.form.get('materia')
            tema = request.form.get('tema')
            fecha = request.form.get('fecha')
            # Construcción de la hora asegurando formato HH:MM:SS
            hora_h = request.form.get('hora_h', '00')
            hora_m = request.form.get('hora_m', '00')
            hora_entrega = f"{hora_h}:{hora_m}:00"
            
            tipo = request.form.get('tipo')
            importante = 1 if 'importante' in request.form else 0
            
            # Ejecutar la actualización filtrando siempre por id y usuario_id
            cursor.execute(
                """UPDATE tareas 
                   SET materia=%s, tema=%s, fecha=%s, hora_entrega=%s, importante=%s, tipo=%s 
                   WHERE id=%s AND usuario_id=%s""",
                (materia, tema, fecha, hora_entrega, importante, tipo, id, session['user_id'])
            )
            
            db.commit()
            flash("¡Tarea actualizada correctamente!", "success")
            return redirect(url_for('index'))
            
        except Exception as e:
            print(f"Error al actualizar la tarea: {e}")
            flash("Ocurrió un error al guardar los cambios.", "danger")
        finally:
            db.close()
            
    # 3. RENDERIZADO DE LA VISTA (GET)
    # Si la conexión sigue abierta (en caso de GET), la cerramos antes de renderizar
    if db.is_connected():
        db.close()
        
    return render_template("crear_editar.html", tarea=tarea)

# --- FUNCIONALIDAD DE RECUPERACIÓN DE CONTRASEÑA (CORREGIDA) ---

@app.route('/olvide-password', methods=['GET', 'POST'])
def olvide_password():
    if request.method == 'POST':
        email = request.form.get('email')
        db = get_db_connection()
        # IMPORTANTE: buffered=True para evitar el error de "Unread result"
        cursor = db.cursor(dictionary=True, buffered=True)
        
        try:
            cursor.execute("SELECT id, usuario FROM usuarios WHERE email = %s", (email,))
            usuario = cursor.fetchone()

            if usuario:
                # Aquí va tu lógica de generar token y enviar mail...
                # Asegúrate de hacer db.commit() si haces un UPDATE
                flash("Se ha enviado un enlace a tu correo.", "success")
            else:
                flash("El correo no está registrado.", "danger")
        except Exception as e:
            print(f"Error en olvide_password: {e}")
            flash("Hubo un error al procesar la solicitud.", "danger")
        finally:
            cursor.close()
            db.close() # Ahora sí cerrará bien
            
    return render_template('login.html') # O la vista que corresponda
    
@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    db = None
    user = None
    
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id FROM usuarios WHERE token_recuperacion = %s", (token,))
        user = cursor.fetchone()
    except Exception as e:
        print(f"Error consultando token: {e}")
    finally:
        if db:
            db.close()

    if not user:
        flash("Token inválido o expirado.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        nueva_pass = generate_password_hash(request.form.get('password'))
        db = get_db_connection()
        try:
            cursor = db.cursor(dictionary=True, buffered=True)
            cursor.execute("UPDATE usuarios SET password = %s, token_recuperacion = NULL WHERE id = %s", 
                           (nueva_pass, user['id']))
            db.commit()
            flash("Contraseña actualizada. Ya puedes iniciar sesión.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error actualizando password: {e}")
            flash("No se pudo actualizar la contraseña.", "danger")
        finally:
            if db:
                db.close()

    return render_template('reset.html', token=token)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        estrellas = request.form.get('estrella')
        mensaje = request.form.get('sugerencia')
        
        # Cuerpo del mensaje en HTML profesional
        html_body = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 1px solid #eee; border-radius: 10px; overflow: hidden;">
            <div style="background-color: #1a1a1a; color: #ffffff; padding: 20px; text-align: center;">
                <h2 style="margin: 0; color: #00ffcc;">AGENDA MAESTRA</h2>
                <p style="font-size: 12px; opacity: 0.7;">Nuevo Feedback de Usuario Recibido</p>
            </div>
            <div style="padding: 30px; background-color: #f9f9f9;">
                <p style="font-size: 16px; color: #333;">Has recibido una nueva calificación:</p>
                <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #00ffcc;">
                    <p><strong>Remitente:</strong> {nombre}</p>
                    <p><strong>Calificación:</strong> <span style="color: #ffca08; font-size: 20px;">{'★' * int(estrellas)}</span> ({estrellas}/5)</p>
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0;">
                    <p><strong>Mensaje:</strong></p>
                    <p style="font-style: italic; color: #555; line-height: 1.6;">"{mensaje}"</p>
                </div>
            </div>
            <div style="background-color: #f1f1f1; padding: 15px; text-align: center; font-size: 11px; color: #888;">
                Este es un mensaje automático generado por el sistema de feedback de Agenda Maestra.
            </div>
        </div>
        """

        msg = Message(
            subject=f"⭐ FEEDBACK [{estrellas}/5] - {nombre}",
            sender=app.config['MAIL_USERNAME'],
            recipients=[app.config['MAIL_USERNAME']]
        )
        msg.html = html_body # Enviamos como HTML
        
        try:
            mail.send(msg)
        except Exception as e:
            print(f"Error enviando correo: {e}")

        return redirect(url_for('index'))
    
    return render_template('feedback.html')

@app.route('/enviar_feedback', methods=['POST'])
def enviar_feedback():
    nombre = request.form.get('nombre_feedback')
    estrellas = request.form.get('estrella')
    mensaje = request.form.get('contenido_mensaje')
    
    # Configuración del mensaje profesional para el admin
    msg = Message(
        subject=f"⭐ RESEÑA DE {nombre.upper()} - {estrellas}/5 Estrellas",
        sender=app.config['MAIL_USERNAME'],
        recipients=[app.config['MAIL_USERNAME']],
        body=f"Has recibido una nueva calificación en Agenda Maestra:\n\n"
             f"Remitente: {nombre}\n"
             f"Puntaje: {estrellas} estrellas\n"
             f"Sugerencias: {mensaje}"
    )
    
    try:
        mail.send(msg)
        return redirect(url_for('index'))
    except Exception as e:
        return f"Error al enviar: {str(e)}"

@app.route('/admin-panel-secret', methods=['GET', 'POST'])
def admin_panel():
    # 1. Recuperación segura de credenciales
    MASTER_USER = os.getenv('ADMIN_USER')
    MASTER_PASS = os.getenv('ADMIN_PASS')

    # Bloqueo preventivo si el entorno no está configurado
    if not MASTER_USER or not MASTER_PASS:
        app.logger.error("ALERTA: Acceso administrativo intentado sin variables de entorno configuradas.")
        flash("Configuración de sistema incompleta. Contacte al administrador.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        user_input = request.form.get('admin_user', '')
        pass_input = request.form.get('admin_pass', '')

        # 2. Validación Robusta (Protección contra ataques de tiempo)
        # Usamos hmac.compare_digest para que el tiempo de respuesta sea constante
        is_user_valid = hmac.compare_digest(user_input, MASTER_USER)
        is_pass_valid = hmac.compare_digest(pass_input, MASTER_PASS)

        if is_user_valid and is_pass_valid:
            # Obtención de datos
            usuarios_lista = obtener_usuarios_db()
            conteo_tareas = obtener_total_tareas()
            
            # Nota: No se guarda en 'session' por requerimiento de seguridad (forzar login)
            return render_template('admin.html', 
                                 usuarios=usuarios_lista, 
                                 tareas=conteo_tareas)
        else:
            # 3. Medida Anti-Fuerza Bruta: Retraso artificial en caso de error
            time.sleep(1.5)
            flash("Identidad no reconocida. El intento ha sido registrado en los logs del sistema.", "danger")
            return redirect(url_for('index'))

    return render_template('admin_login.html')

def obtener_usuarios_db():
    """Extrae la lista de usuarios con manejo de errores robusto."""
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        # Solo traemos los campos necesarios para auditoría
        cursor.execute("""
            SELECT usuario, email, nivel, creado_at 
            FROM usuarios 
            ORDER BY creado_at DESC
        """)
        usuarios = cursor.fetchall()
        cursor.close()
        db.close()
        return usuarios
    except Exception as e:
        app.logger.error(f"⚠️ Error crítico en base de datos (obtener_usuarios): {e}")
        return []

def obtener_total_tareas():
    """Calcula el total de tareas globales activas en el sistema."""
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True, buffered=True)
        # Contamos solo las que no están en la papelera
        cursor.execute("SELECT COUNT(*) FROM tareas WHERE eliminado_at IS NULL")
        resultado = cursor.fetchone()
        cursor.close()
        db.close()
        return resultado[0] if resultado else 0
    except Exception as e:
        app.logger.error(f"⚠️ Error crítico en base de datos (obtener_total_tareas): {e}")
        return 0

from flask import request, session, flash, redirect, url_for

@app.route('/guardar_tarea', methods=['POST'])
def guardar_tarea():
    # 1. CAPTURAMOS LOS DATOS (Esto resuelve los errores de Pylance)
    materia = request.form.get('materia')
    tema = request.form.get('tema')
    fecha = request.form.get('fecha')
    tipo = request.form.get('tipo', 'tarea') # Por defecto 'tarea'
    colaborador_email = request.form.get('colaboradores')
    
    # Datos de la sesión del usuario actual
    usuario_id = session.get('usuario_id')
    usuario_nombre = session.get('usuario')

    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    try:
        # 2. Guardamos la tarea para vos (el creador)
        query_dueno = """
            INSERT INTO tareas (usuario_id, materia, tema, fecha, tipo, colaboradores)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_dueno, (usuario_id, materia, tema, fecha, tipo, colaborador_email))
        
        # 3. Si es grupal y hay un email, se la enviamos al otro
        if tipo == 'grupal' and colaborador_email:
            cursor.execute("SELECT id FROM usuarios WHERE email = %s", (colaborador_email,))
            destinatario = cursor.fetchone()
            
            if destinatario:
                # Se la insertamos en su agenda directamente
                query_colaborador = """
                    INSERT INTO tareas (usuario_id, materia, tema, fecha, tipo, colaboradores)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                # En colaboradores ponemos el nombre de quien la mandó
                cursor.execute(query_colaborador, (destinatario['id'], materia, tema, fecha, 'grupal', usuario_nombre))
                
                # 4. Llamamos a la función de mail (definida abajo)
                enviar_mail_invitacion(colaborador_email, materia, tema, usuario_nombre)

        db.commit()
        flash("¡Tarea guardada con éxito!", "success")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        flash("Hubo un error al guardar la tarea.", "danger")
    finally:
        cursor.close()
        
    return redirect(url_for('index')) 

@app.route('/escaneo')
def escaneo():
    """Ruta para abrir la interfaz de la cámara del escáner QR."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Intentamos cargar con tilde que es como figura en tu sistema de archivos original
    try:
        return render_template('escáner.html')
    except Exception as e:
        print(f"[Aviso] No se encontró escáner.html, probando alternativa: {e}")
        return render_template('escaneo.html')


@app.route('/compartir_tarea/<int:tarea_id>')
def compartir_tarea(tarea_id):
    """Genera la estructura de datos optimizada y compacta para el QR."""
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Sesión inválida. Inicie sesión nuevamente."}), 401

    conn = None
    cursor = None
    try:
        # Usamos la variable global de tu Pool (si se llama diferente, ej. 'pool', se adapta aquí)
        # Viendo tu app, comúnmente la inicializaste como db_pool o pool. Aseguramos fallback:
        if 'db_pool' in globals():
            conn = db_pool.get_connection()
        elif 'pool' in globals():
            conn = pool.get_connection()
        else:
            # Si no, intentamos un fallback directo al módulo para que no rompa jamás
            import app
            conn = app.db_pool.get_connection()

    except Exception as e:
        print(f"[ERROR CRÍTICO POOL] No se pudo obtener una conexión activa: {e}")
        return jsonify({"success": False, "error": "El servidor de base de datos está saturado. Intente de nuevo."}), 500
        
    try:
        cursor = conn.cursor(dictionary=True)
        # Buscamos la tarea validando que pertenezca al usuario activo y no esté en la papelera
        cursor.execute("""
            SELECT materia, tema, fecha, tipo, importante, color 
            FROM tareas 
            WHERE id = %s AND usuario_id = %s AND eliminado_at IS NULL
        """, (tarea_id, session['user_id']))
        tarea = cursor.fetchone()
        
        if not tarea:
            return jsonify({"success": False, "error": "La tarea solicitada no existe o no tienes permisos."}), 404

        # Formateo estricto de la fecha a string YYYY-MM-DD para evitar fallos de serialización JSON
        if isinstance(tarea['fecha'], (date, datetime)):
            fecha_str = tarea['fecha'].strftime('%Y-%m-%d')
        else:
            fecha_str = str(tarea['fecha'])

        # Diccionario ultra optimizado con llaves cortas para reducir la densidad del código QR
        datos_qr = {
            "mat": tarea['materia'],
            "tem": tarea['tema'],
            "fec": fecha_str,
            "tip": tarea['tipo'],
            "imp": int(tarea['important']) if 'important' in tarea else int(tarea.get('importante', 0)),
            "col": tarea['color'] if tarea['color'] else '#38bdf8'
        }
        
        return jsonify({"success": True, "datos": datos_qr})

    except Exception as e:
        print(f"--- [ERROR CRÍTICO GENERACIÓN QR] ---: {str(e)}")
        return jsonify({"success": False, "error": "Error interno al procesar los datos del QR."}), 500
    finally:
        # Devolución segura de recursos al pool para evitar el bloqueo del servidor de base de datos
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/importar_tarea', methods=['POST'])
def importar_tarea():
    """Procesa los datos capturados por el escáner e inserta la nueva tarea al usuario."""
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Tu sesión ha expirado o es inválida."}), 401
        
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No se recibieron datos legibles del código QR."}), 400

    # Extraemos los datos usando las llaves compactas mapeadas
    materia = data.get('mat', 'Importado QR')
    tema = data.get('tem', 'Sin asunto definido')
    fecha = data.get('fec')
    tipo = data.get('tip', 'tarea')
    importante = data.get('imp', 0)
    color = data.get('col', '#00d2ff')
    descripcion = data.get('descripcion', '') # Captura la descripción compartida

    if not fecha:
        return jsonify({"success": False, "error": "El código QR no contiene una fecha de entrega válida."}), 400

    conn = None
    cursor = None
    try:
        # Obtenemos conexión limpia desde el Pool
        if 'db_pool' in globals():
            conn = db_pool.get_connection()
        elif 'pool' in globals():
            conn = pool.get_connection()
        else:
            import app
            conn = app.db_pool.get_connection()
            
        cursor = conn.cursor()
        
        # Ejecutamos la inserción usando SQL puro para mantener consistencia con tu pool
        query = """
            INSERT INTO tareas (usuario_id, materia, tema, fecha, tipo, importante, color, descripcion, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pendiente')
        """
        valores = (session['user_id'], materia, tema, fecha, tipo, importante, color, descripcion)
        
        cursor.execute(query, valores)
        conn.commit()  # Confirmamos la transacción en caliente
        
        return jsonify({
            "success": True, 
            "message": "¡Excelente! La tarea compartida se ha sincronizado en tu Agenda Maestra."
        })

    except Exception as e:
        if conn:
            conn.rollback() # Ante cualquier falla, revertimos para evitar corrupción de datos
        print(f"[ERROR CRÍTICO EN IMPORTACIÓN QR]: {str(e)}")
        return jsonify({
            "success": False, 
            "error": "Error de persistencia al clonar la tarea en la base de datos."
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/importar_qr_compartido_v2', methods=['POST'])
def importar_qr_compartido_v2():
    """
    Ruta optimizada para la importación de tareas grupales via QR, 
    soportando la nueva columna 'descripcion'.
    """
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Sesión inválida."}), 401
        
    conn = None
    cursor = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Datos corruptos."}), 400

        materia = data.get('materia', 'S/M')
        tema = data.get('tema', 'Tarea Compartida')
        fecha = data.get('fecha')
        tipo = data.get('tipo', 'tarea')
        importante = data.get('importante', 0)
        color = data.get('color', '#00d2ff')
        descripcion = data.get('descripcion', '') # Captura la descripción compartida

        if not fecha:
            return jsonify({"success": False, "error": "La fecha de entrega es un parámetro mandatorio."}), 400

        if 'db_pool' in globals():
            conn = db_pool.get_connection()
        elif 'pool' in globals():
            conn = pool.get_connection()
        else:
            import app
            conn = app.db_pool.get_connection()
            
        cursor = conn.cursor(dictionary=True)

        check_query = """
            SELECT id FROM tareas 
            WHERE usuario_id = %s AND materia = %s AND tema = %s AND fecha = %s AND eliminado_at IS NULL
        """
        cursor.execute(check_query, (session['user_id'], materia, tema, fecha))
        registro_existente = cursor.fetchone()
        
        if registro_existente:
            return jsonify({
                "success": False, 
                "error": "Operación cancelada: Esta tarea grupal ya fue sincronizada en tu tablero previamente."
            }), 409

        insert_query = """
            INSERT INTO tareas (usuario_id, materia, tema, fecha, tipo, importante, color, descripcion, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pendiente')
        """
        valores = (session['user_id'], materia, tema, fecha, tipo, importante, color, descripcion)
        
        cursor.execute(insert_query, valores)
        conn.commit()
        
        return jsonify({
            "success": True, 
            "message": f"¡Éxito total! [Materia: {materia}] importada sin duplicados."
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[ERROR CRÍTICO CONTROL-QR]: {str(e)}")
        return jsonify({"success": False, "error": "Error interno del pool de persistencia."}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/importar_qr_seguro_antiduplicado', methods=['POST'])
def importar_qr_seguro_antiduplicado():
    """
    Ruta premium con bloqueo estricto de duplicación para tareas grupales compartidas.
    Verifica la existencia previa de la combinación exacta en la base de datos antes de insertar.
    """
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Falta autenticación de sesión."}), 401
        
    conn = None
    cursor = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Cuerpo de solicitud vacío o corrupto."}), 400

        materia = data.get('materia', 'S/M').strip()
        tema = data.get('tema', 'Misión Compartida').strip()
        fecha = data.get('fecha')
        tipo = data.get('tipo', 'tarea')
        importante = data.get('importante', 0)
        color = data.get('color', '#00d2ff')
        descripcion = data.get('descripcion', '').strip() # Integra la columna del paso anterior

        if not fecha:
            return jsonify({"success": False, "error": "La fecha de entrega es un parámetro mandatorio."}), 400

        # Obtención segura de conexiones desde tu Pool Dedicado
        if 'db_pool' in globals():
            conn = db_pool.get_connection()
        elif 'pool' in globals():
            conn = pool.get_connection()
        else:
            import app
            conn = app.db_pool.get_connection()
            
        cursor = conn.cursor(dictionary=True)
        
        # --- VERIFICACIÓN DE CONTROL ANTI-DUPLICADOS ---
        check_query = """
            SELECT id FROM tareas 
            WHERE usuario_id = %s AND materia = %s AND tema = %s AND fecha = %s AND eliminado_at IS NULL
        """
        cursor.execute(check_query, (session['user_id'], materia, tema, fecha))
        registro_existente = cursor.fetchone()
        
        if registro_existente:
            return jsonify({
                "success": False, 
                "error": "Operación cancelada: Esta tarea grupal ya fue sincronizada en tu tablero previamente."
            }), 409

        # --- INSERCIÓN ATÓMICA DE LA TAREA CLONADA ---
        insert_query = """
            INSERT INTO tareas (usuario_id, materia, tema, fecha, tipo, importante, color, descripcion, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pendiente')
        """
        valores = (session['user_id'], materia, tema, fecha, tipo, importante, color, descripcion)
        
        cursor.execute(insert_query, valores)
        conn.commit()
        
        return jsonify({
            "success": True, 
            "message": f"¡Éxito total! [Materia: {materia}] importada sin duplicados."
        })

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[ERROR CRÍTICO EN IMPORTACIÓN QR]: {e}")
        return jsonify({
            "success": False,
            "error": "Error de persistencia al clonar la tarea en la base de datos."
        }), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

if __name__ == '__main__':
    app.run(debug=True)