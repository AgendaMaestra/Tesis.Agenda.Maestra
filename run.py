from app import app
from waitress import serve
import socket
import os
import multiprocessing
import urllib.parse
import webbrowser
import sys

def obtener_ip_local():
    """Detecta la IP privada real de la PC de forma robusta."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip_detectada = s.getsockname()[0]
    except Exception:
        try:
            ip_detectada = socket.gethostbyname(socket.gethostname())
        except:
            ip_detectada = "127.0.0.1"
    finally:
        s.close()
    return ip_detectada

def abrir_qr_navegador(url_destino):
    """Genera un QR visual a través de API y lo abre en el navegador predeterminado."""
    try:
        url_segura = urllib.parse.quote(url_destino, safe='')
        api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={url_segura}"
        webbrowser.open(api_url, new=2) 
        return True
    except Exception as e:
        print(f"[!] No se pudo abrir el navegador: {e}")
        return False

if __name__ == "__main__":
    # 1. Configuración de parámetros
    puerto = 5000
    hilos = (multiprocessing.cpu_count() * 2) + 1
    
    # --- CONFIGURACIÓN DE NGROK ---
    # Reemplaza esta URL si Ngrok te da una nueva al reiniciar
    url_ngrok = "https://equity-perfected-request.ngrok-free.dev"
    
    # 2. Estética de la Terminal
    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*65)
    print("             AGENDA MAESTRA - MODO NGROK ACTIVO             ")
    print("="*65)
    print(f" ► ACCESO SEGURO (Móvil): {url_ngrok}")
    print(f" ► ACCESO LOCAL (PC):    http://localhost:{puerto}")
    print("-" * 65)
    print(f" [i] RENDIMIENTO: {hilos} hilos | Límite: 1000 conexiones")
    print(f" [i] ESTADO:      Túnel seguro habilitado para Cámara/QR")
    print("="*65)

    # 3. Lanzar QR de Ngrok
    print("\n QR GENERADO: Escanea el código en el navegador para tu móvil.")
    abrir_qr_navegador(url_ngrok)

    # 4. Ejecución del servidor Waitress
    try:
        serve(
            app, 
            host='0.0.0.0', 
            port=puerto, 
            threads=hilos,
            connection_limit=1000,
            channel_timeout=60,
            backlog=2048
        )
    except KeyboardInterrupt:
        print("\n[!] Servidor detenido por el usuario.")
        sys.exit(0)