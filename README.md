# 🎯 Agenda Maestra v2026: Productividad Gamificada

**Agenda Maestra** es una plataforma integral de gestión del tiempo y optimización del rendimiento académico que fusiona la productividad tradicional con dinámicas de videojuegos (Gamification)[cite: 21, 22]. El sistema está diseñado para transformar la carga académica en una serie de objetivos gratificantes, reduciendo la procrastinación mediante un sistema de progreso visual y recompensas estratégicas.

---

## 🚀 Características y Funcionalidades Principales

### 1. Motor de Gamificación Avanzado
*   **Gestión de XP y Niveles**: Cada tarea completada otorga puntos de experiencia (XP) basados en la dificultad, permitiendo al usuario subir de nivel y alcanzar nuevos rangos académicos.
*   **Sistema de Rachas (Streaks)**: Módulo interactivo representado por iconos de fuego que premia la constancia diaria. No completar tareas puede resultar en la pérdida de la racha acumulada[cite: 21].
*   **Panel de Logros**: Seccion dedicada a visualizar trofeos y hitos alcanzados durante el ciclo lectivo[cite: 21].

### 2. Gestión Estratégica de Tareas
*   **Tareas Grupales y Colaborativas**: Capacidad para integrar colaboradores mediante correo electrónico, permitiendo la visualización compartida de objetivos[cite: 14].
*   **Asistencia de Prioridad**: Algoritmo que analiza fechas límite y sugiere automáticamente qué tareas deben resolverse primero para evitar sobrecargas.
*   **Papelera de Recuperación**: Sistema de persistencia que permite recuperar elementos eliminados por error durante un periodo de 48 horas[cite: 17].

### 3. Interfaz y Experiencia de Usuario (UX/UI)
*   **Estilo Glassmorphism**: Estética moderna basada en capas de transparencia, desenfoque de fondo y bordes brillantes[cite: 21, 22].
*   **Diseño Responsivo Total**: Adaptación fluida entre escritorio y dispositivos móviles mediante Media Queries avanzadas[cite: 21, 22].
*   **Feedback de Usuario**: Sistema de calificación de 5 estrellas integrado en el menú de opciones que envía reportes automáticos al administrador vía SMTP.

### 4. Seguridad y Control
*   **Panel Administrativo Oculto**: Acceso restringido mediante combinación de teclas (Ctrl + H) y autenticación forzada por sesión para gestión de backend[cite: 12].
*   **Protección de Datos**: Hashing de contraseñas y validaciones estrictas en el registro para evitar credenciales débiles[cite: 22].

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología | Descripción |
| :--- | :--- | :--- |
| **Backend** | Python 3.10+ | Lógica de servidor y procesamiento de datos. |
| **Framework** | Flask | Micro-framework para la gestión de rutas y plantillas Jinja2. |
| **Base de Datos** | MySQL | Almacenamiento persistente de usuarios, tareas y progreso[cite: 17]. |
| **Frontend** | HTML5 / CSS3 / JS | Arquitectura basada en Grid, Flexbox y JavaScript funcional[cite: 21, 22]. |
| **Email** | Flask-Mail | Integración con servidores SMTP para notificaciones y feedback. |
| **Entorno** | Python-Dotenv | Gestión segura de claves API y credenciales de DB[cite: 12]. |

---

## ⚙️ Configuración del Entorno de Desarrollo

Para replicar este proyecto localmente, sigue estos pasos:

1. **Requisitos Previos**:
   - Tener instalado Python y MySQL Server.
   - Contar con una cuenta de Gmail para la función de envío de correos (requiere Contraseña de Aplicación).

2. **Instalación de Dependencias**:
   ```bash
   pip install flask flask-sqlalchemy flask-mail python-dotenv werkzeug