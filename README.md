# Agenda Maestra v2026

Agenda Maestra es una plataforma de productividad integral diseñada para la optimización del rendimiento académico. El sistema combina mecánicas de gamificación con lógica de asistencia estratégica para facilitar la gestión de tareas y exámenes.

## Público Objetivo
La aplicación está orientada a estudiantes de nivel secundario, universitario y de posgrado, así como a usuarios que busquen reducir la procrastinación mediante un sistema de progreso basado en objetivos y recompensas.

## Características Técnicas y Funcionalidades

* **Sistema de Gamificación**: Implementación de algoritmos para la asignación de puntos de experiencia (XP), gestión de niveles y desbloqueo de rangos basados en la productividad real.
* **Seguimiento de Rachas**: Módulo diseñado para incentivar la constancia diaria mediante el monitoreo de actividad ininterrumpida.
* **Asistencia Estratégica**: Sistema de análisis de carga de trabajo que identifica prioridades críticas y sugiere una secuencia lógica de resolución de tareas.
* **Gestión de Ciclo de Vida de Tareas**: Incluye una papelera de reciclaje con persistencia temporal de 48 horas para la recuperación de datos eliminados.
* **Visualización de Datos**: Calendario dinámico de entregas y panel de analíticas con métricas de rendimiento desglosadas por materia.
* **Interfaz de Usuario**: Diseño basado en Glassmorphism con arquitectura responsiva y soporte para esquemas de color dual (Modo Claro/Oscuro).

## Stack Tecnológico

* **Backend**: Desarrollado en Python utilizando el micro-framework Flask.
* **Base de Datos**: MySQL para la gestión persistente de perfiles de usuario, tareas y registros de gamificación.
* **Frontend**: Arquitectura basada en HTML5, CSS3 (CSS Grid, Flexbox y Variables Personalizadas) y JavaScript funcional.
* **Comunicaciones**: Integración de Flask-Mail para la automatización de notificaciones y recordatorios mediante protocolos SMTP.
* **Seguridad**: Implementación de hashing de credenciales mediante Werkzeug y gestión de entorno a través de python-dotenv.