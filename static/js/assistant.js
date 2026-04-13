/**
 * Inicialización: Aseguramos que el panel empiece oculto al cargar la página.
 */
document.addEventListener('DOMContentLoaded', () => {
    const panel = document.getElementById('ai-panel');
    if (panel) {
        panel.style.display = 'none';
    }
});

/**
 * Función principal para abrir/cerrar el asistente.
 * Combina la detección robusta de estilos y la gestión de errores.
 */
function toggleAssistant() {
    const panel = document.getElementById('ai-panel');
    
    // Verificación de existencia del elemento (de la primera versión)
    if (!panel) {
        console.error("No se encontró el elemento #ai-panel");
        return;
    }
    
    // Lógica de alternancia (Toggle)
    // Comprobamos tanto 'none' como vacío '' para asegurar que funcione en todos los navegadores
    if (panel.style.display === 'none' || panel.style.display === '') {
        panel.style.display = 'block';
        // Si se abre, consultamos los datos a la IA
        fetchAssistantData();
    } else {
        panel.style.display = 'none';
    }
}

/**
 * Realiza la petición asíncrona al servidor para obtener el análisis de la IA.
 */
async function fetchAssistantData() {
    const content = document.getElementById('ai-content');
    
    // Estado de carga inicial
    if (content) {
        content.innerHTML = '<p>Consultando a la IA...</p><div class="loader"></div>';
    }
    
    try {
        // Llamada al endpoint de Python que definimos anteriormente
        const response = await fetch('/ai_analisis');
        
        if (!response.ok) {
            throw new Error('Error en el servidor');
        }
        
        const data = await response.json();
        
        // Construcción del HTML dinámico
        let html = `
            <strong>¡Hola ${data.usuario}!</strong>
            <p style="margin-top:5px; opacity:0.8;">${data.mensaje_intro}</p>
            <hr style="border:0; border-top:1px solid rgba(255,255,255,0.1); margin:10px 0;">
        `;
        
        // Verificación de si existen tareas en la respuesta
        if (data.tareas && data.tareas.length > 0) {
            data.tareas.forEach(t => {
                html += `
                <div class="ai-task-item" style="background: rgba(255,255,255,0.05); padding:10px; border-radius:10px; margin-bottom:8px; border-left:3px solid var(--accent);">
                    <div style="font-weight:bold; color:var(--accent)">${t.tema}</div>
                    <div style="font-size:0.75rem; opacity:0.8; color:var(--text-secondary);">${t.materia}</div>
                    <div style="font-size:0.75rem; font-weight:bold; margin-top:4px;">${t.tiempo_restante}</div>
                </div>`;
            });
        } else {
            // Caso en que el array de tareas esté vacío
            html += "<p>No encontré tareas pendientes. ¡Día libre! ☕</p>";
        }
        
        // Inyectamos el contenido final
        if (content) {
            content.innerHTML = html;
        }

    } catch (error) {
        // Gestión de errores visuales para el usuario
        console.error("Error al obtener datos del asistente:", error);
        if (content) {
            content.innerHTML = "<p style='color:#ff4747;'>⚠️ No se pudo conectar con el servidor.</p>";
        }
    }
}

/**
 * Controla la visibilidad del modal de ayuda
 */
function toggleHelp() {
    const helpModal = document.getElementById('help-modal');
    if (!helpModal) return;

    if (helpModal.style.display === 'none' || helpModal.style.display === '') {
        // Si abrimos la ayuda, cerramos el asistente IA para no amontonar
        const aiPanel = document.getElementById('ai-panel');
        if (aiPanel) aiPanel.style.display = 'none';
        
        helpModal.style.display = 'block';
    } else {
        helpModal.style.display = 'none';
    }
}

// Opcional: Cerrar la ayuda si se hace clic fuera de ella
document.addEventListener('mousedown', (event) => {
    const helpContainer = document.getElementById('help-container');
    const helpModal = document.getElementById('help-modal');
    
    if (helpModal && helpModal.style.display === 'block') {
        if (!helpContainer.contains(event.target)) {
            helpModal.style.display = 'none';
        }
    }
});

const nuevaAyuda = `
    <div class="help-step">
        <strong>🧹 Vaciar Papelera:</strong> Dentro de la papelera, aparecerá un botón rojo para borrar todo definitivamente.
    </div>
`;