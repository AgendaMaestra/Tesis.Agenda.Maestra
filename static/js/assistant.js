function analizarPrioridades() {
    const content = document.getElementById('ai-content');
    const scanner = document.querySelector('.scanner-line');
    
    // Mostramos el escáner
    if(scanner) scanner.style.display = 'block';
    content.innerHTML = '<div class="loading-text">Analizando tu carga académica...</div>';

    // Simulamos un retraso de "procesamiento" para realismo
    setTimeout(() => {
        if(scanner) scanner.style.display = 'none';
        
        const tareas = document.querySelectorAll('.tarea-card'); // Ajusta segun tu clase de tareas
        let countImportantes = 0;
        
        tareas.forEach(t => {
            if(t.innerHTML.includes('★')) countImportantes++;
        });

        let consejo = countImportantes > 0 
            ? `Detecto ${countImportantes} tareas críticas. Prioriza los puntos estrella para proteger tu racha.` 
            : "No hay amenazas críticas hoy. ¡Buen momento para adelantar trabajo!";

        content.innerHTML = `
            <div style="animation: fadeIn 0.5s ease;">
                <h4 style="color: var(--accent); margin-bottom:10px;">Análisis de Sistema</h4>
                <p style="font-size: 0.9rem; line-height: 1.4; opacity: 0.9;">${consejo}</p>
                <hr style="border: 0; border-top: 1px solid var(--glass-border); margin: 15px 0;">
                <small style="opacity: 0.6;">Estado: Operativo v2.0</small>
            </div>
        `;
    }, 1200);
}

document.addEventListener('DOMContentLoaded', () => {
    const panel = document.getElementById('ai-panel');
    if (panel) {
        panel.style.display = 'none';
    }
});

function toggleAssistant() {
    const panel = document.getElementById('ai-panel');
    const helpModal = document.getElementById('help-modal');
    
    if (panel.style.display === 'none' || panel.style.display === '') {
        // Cerrar la ayuda si está abierta para evitar solapamientos
        if (helpModal) helpModal.style.display = 'none';
        
        panel.style.display = 'block';
        panel.classList.add('animate-in'); // Puedes añadir una animación CSS
    } else {
        panel.style.display = 'none';
    }
}

// Cerrar con la tecla Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.getElementById('ai-panel').style.display = 'none';
    }
});

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

function toggleHelp() {
    const modal = document.getElementById('help-modal');
    const isVisible = modal.style.display === 'block';
    
    // Cerramos el panel de la IA si abrimos la ayuda para no saturar la pantalla
    const aiPanel = document.getElementById('ai-panel');
    if (!isVisible && aiPanel) aiPanel.style.display = 'none';

    modal.style.display = isVisible ? 'none' : 'block';
}

// Cerrar al hacer clic fuera del contenedor
document.addEventListener('click', function(event) {
    const container = document.getElementById('help-container');
    const modal = document.getElementById('help-modal');
    if (!container.contains(event.target)) {
        modal.style.display = 'none';
    }
});