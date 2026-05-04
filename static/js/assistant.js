function analizarPrioridades() {
    const content = document.getElementById('ai-content');
    const scanner = document.querySelector('.ai-scanner-bar, .scanner-line');

    if (scanner) scanner.style.display = 'block';
    content.innerHTML = '<div class="loading-text">Buscando tareas...</div>';

    setTimeout(() => {
        if (scanner) scanner.style.display = 'none';

        const tareas = Array.from(document.querySelectorAll('.tarea-card'));
        let countImportantes = 0;
        let totalTareas = tareas.length;
        let completadas = 0;
        const resumenTareas = [];

        tareas.forEach(t => {
            const texto = t.innerText || '';
            const urgente = texto.includes('★');
            if (urgente) {
                countImportantes++;
            }

            const statusIcon = t.querySelector('.status-icon');
            const estado = statusIcon ? statusIcon.innerText.trim() : '⭕';
            if (estado === '✅' || estado === '✓') {
                completadas++;
            }

            const materia = t.querySelector('.materia-tag')?.innerText.trim() || '';
            const tema = t.querySelector('.tema-title')?.innerText.trim() || '';
            const fecha = t.querySelector('.meta-data')?.innerText.trim() || '';
            resumenTareas.push({ tema, materia, fecha, estado, urgente });
        });

        const pendientes = Math.max(0, totalTareas - completadas);

        let informe = '';
        if (totalTareas === 0) {
            informe = 'No hay tareas. Agrega una nueva para empezar.';
        } else {
            informe = `Tienes <strong>${totalTareas}</strong> tareas, <strong>${pendientes}</strong> pendientes y <strong>${completadas}</strong> completas. `;
            if (countImportantes > 0) {
                informe += `Hay <strong>${countImportantes}</strong> tareas con ★. Atiende esas antes.`;
            } else {
                informe += 'No hay prioridades altas. Avanza con las tareas pendientes.';
            }
        }

        const tareasOrdenadas = resumenTareas.sort((a, b) => (b.urgente ? 1 : 0) - (a.urgente ? 1 : 0));
        let detalleHTML = '';
        if (tareasOrdenadas.length > 0) {
            const visibles = tareasOrdenadas.slice(0, 3);
            detalleHTML = '<div style="margin-top: 12px; display: flex; flex-direction: column; gap: 8px; text-align: left;">';
            visibles.forEach(item => {
                const icono = item.urgente ? '🔴' : '⚪';
                detalleHTML += `
                    <div style="background: rgba(255,255,255,0.05); padding: 10px 12px; border-radius: 10px; border-left: 3px solid rgba(56, 189, 248, 0.4); display: flex; align-items: flex-start; gap: 10px;">
                        <span style="font-size: 1.2rem; flex-shrink: 0;">${icono}</span>
                        <div style="min-width: 0; flex: 1;">
                            <div style="font-size: 0.9rem; font-weight: 600; color: #fff; word-break: break-word;">${item.tema || 'Sin título'}</div>
                            <div style="margin-top: 4px; font-size: 0.75rem; color: rgba(255,255,255,0.6); line-height: 1.3;">
                                ${item.materia ? `${item.materia} · ` : ''}${item.fecha || ''}
                            </div>
                        </div>
                        <span style="font-size: 0.9rem; flex-shrink: 0; margin-top: 2px;">${item.estado}</span>
                    </div>`;
            });
            detalleHTML += '</div>';
        }

        const extraTexto = totalTareas > 3 ? `<p style="margin-top: 10px; font-size: 0.75rem; color: rgba(255,255,255,0.5);">+${totalTareas - 3} más</p>` : '';

        content.innerHTML = `
            <div style="animation: fadeIn 0.5s ease; padding: 12px 10px;">
                <div style="margin-bottom: 10px;">
                    <h4 style="color: var(--accent); margin: 0 0 6px 0; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">Estado</h4>
                    <p style="margin: 0; font-size: 0.82rem; line-height: 1.4; color: rgba(255,255,255,0.85);">${informe}</p>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px; margin-bottom: 12px;">
                    <div style="background: rgba(56, 189, 248, 0.1); padding: 8px 10px; border-radius: 10px; color: #a8d8ff; font-size: 0.75rem; border: 1px solid rgba(56, 189, 248, 0.15); text-align: center;">
                        Total<br><strong style="font-size: 0.95rem;">${totalTareas}</strong>
                    </div>
                    <div style="background: rgba(255, 71, 87, 0.1); padding: 8px 10px; border-radius: 10px; color: #ffa8b8; font-size: 0.75rem; border: 1px solid rgba(255, 71, 87, 0.15); text-align: center;">
                        Pendientes<br><strong style="font-size: 0.95rem;">${pendientes}</strong>
                    </div>
                </div>
                ${detalleHTML}
                ${extraTexto}
            </div>
        `;
    }, 700);
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

// Cerrar al hacer clic fuera del contenedor
document.addEventListener('click', function(event) {
    const container = document.getElementById('help-container-root');
    const modal = document.getElementById('help-modal');
    if (modal && modal.style.display === 'block' && container && !container.contains(event.target)) {
        modal.style.display = 'none';
    }
});

function toggleMenu(event) {
    event.stopPropagation();
    const menu = document.getElementById('dropdown-perfil');
    menu.classList.toggle('active');
}

// 2. FUNCION PARA AMPLIAR LA IMAGEN
function abrirModalImagen() {
    const modal = document.getElementById('modalImagen');
    modal.style.display = 'flex';
    // Cerramos el menú al abrir el modal
    document.getElementById('dropdown-perfil').classList.remove('active');
}

function cerrarModal() {
    document.getElementById('modalImagen').style.display = 'none';
}

// 3. CERRAR MENU SI SE TOCA FUERA
document.addEventListener('click', function() {
    const menu = document.getElementById('dropdown-perfil');
    if (menu) menu.classList.remove('active');
});