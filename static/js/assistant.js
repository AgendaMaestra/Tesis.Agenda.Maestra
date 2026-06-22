let pomodoroIntervalo = null;
let tiempoRestante = 25 * 60;
let modoPomodoroActivo = "estudio"; 

function crearContenedorEnfoque() {
    if (document.getElementById('pomodoro-focus-container')) return;

    const contenedor = document.createElement('div');
    contenedor.id = 'pomodoro-focus-container';
    contenedor.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(15, 23, 42, 0.98); backdrop-filter: blur(20px);
        z-index: 9999; display: none; align-items: center; justify-content: center;
        flex-direction: column; color: #fff; font-family: inherit;
    `;

    contenedor.innerHTML = `
        <div style="text-align: center; max-width: 450px; width: 90%; padding: 30px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 24px; box-shadow: 0 20px 50px rgba(0,0,0,0.5);">
            <div id="enfoque-badge" style="background: var(--error); display: inline-block; padding: 6px 16px; border-radius: 50px; font-size: 0.75rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 15px; box-shadow: 0 0 15px var(--error);">
                ⚡ MODO ENFOQUE ACTIVO
            </div>
            <h2 id="enfoque-tarea-titulo" style="margin: 10px 0; font-size: 1.4rem; font-weight: 800; color: #fff;">Misión Seleccionada</h2>
            <p id="enfoque-materia-tag" style="color: var(--accent); font-weight: 700; font-size: 0.9rem; margin-top: 0; opacity: 0.8;">Materia</p>
            
            <div style="margin: 40px auto; width: 200px; height: 200px; border-radius: 50%; border: 6px solid rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center; position: relative;">
                <div id="pomodoro-timer-display" style="font-size: 3rem; font-weight: 900; font-variant-numeric: tabular-nums; letter-spacing: -1px; background: linear-gradient(90deg, #fff, var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">25:00</div>
            </div>

            <div style="display: flex; gap: 10px; justify-content: center; margin-bottom: 25px;">
                <button id="btn-pomo-play" onclick="controlarPomodoro('start')" style="background: var(--success); color: #0f172a; border: none; padding: 12px 25px; border-radius: 12px; font-weight: 800; cursor: pointer; transition: all 0.2s;">INICIAR</button>
                <button id="btn-pomo-pause" onclick="controlarPomodoro('pause')" style="background: rgba(255,255,255,0.08); color: #fff; border: 1px solid rgba(255,255,255,0.1); padding: 12px 25px; border-radius: 12px; font-weight: 800; cursor: pointer; display: none;">PAUSAR</button>
                <button onclick="controlarPomodoro('reset')" style="background: rgba(255,71,87,0.1); color: var(--error); border: 1px solid rgba(255,71,87,0.2); padding: 12px 20px; border-radius: 12px; font-weight: 800; cursor: pointer;">REINICIAR</button>
            </div>

            <button onclick="cerrarModoEnfoque()" style="background: transparent; border: none; color: var(--text-muted); font-size: 0.85rem; font-weight: 700; cursor: pointer; text-decoration: underline; opacity: 0.6; transition: opacity 0.2s;">Salir del Modo Enfoque e Interrumpir Misión</button>
        </div>
    `;

    document.body.appendChild(contenedor);
}

function activarModoEnfoque(tema, materia) {
    crearContenedorEnfoque();
    document.getElementById('enfoque-tarea-titulo').innerText = tema;
    document.getElementById('enfoque-materia-tag').innerText = `📚 MATERIA: ${materia.toUpperCase()}`;
    
    modoPomodoroActivo = "estudio";
    tiempoRestante = 25 * 60;
    actualizarDisplayPomodoro();

    document.getElementById('pomodoro-focus-container').style.display = 'flex';
}

function actualizarDisplayPomodoro() {
    const minutos = Math.floor(tiempoRestante / 60);
    const segundos = tiempoRestante % 60;
    const textoTime = `${minutos.toString().padStart(2, '0')}:${segundos.toString().padStart(2, '0')}`;
    const display = document.getElementById('pomodoro-timer-display');
    if (display) display.innerText = textoTime;
}

function controlarPomodoro(accion) {
    const btnPlay = document.getElementById('btn-pomo-play');
    const btnPause = document.getElementById('btn-pomo-pause');

    if (accion === 'start') {
        if (pomodoroIntervalo) return;
        if (btnPlay) btnPlay.style.display = 'none';
        if (btnPause) btnPause.style.display = 'inline-block';
        
        pomodoroIntervalo = setInterval(() => {
            if (tiempoRestante > 0) {
                tiempoRestante--;
                actualizarDisplayPomodoro();
            } else {
                clearInterval(pomodoroIntervalo);
                pomodoroIntervalo = null;
                ejecutarAlertaCicloCompleto();
            }
        }, 1000);
    } else if (accion === 'pause') {
        clearInterval(pomodoroIntervalo);
        pomodoroIntervalo = null;
        if (btnPlay) btnPlay.style.display = 'inline-block';
        if (btnPause) btnPause.style.display = 'none';
    } else if (accion === 'reset') {
        clearInterval(pomodoroIntervalo);
        pomodoroIntervalo = null;
        tiempoRestante = modoPomodoroActivo === "estudio" ? 25 * 60 : 5 * 60;
        actualizarDisplayPomodoro();
        if (btnPlay) btnPlay.style.display = 'inline-block';
        if (btnPause) btnPause.style.display = 'none';
    }
}

function ejecutarAlertaCicloCompleto() {
    const badge = document.getElementById('enfoque-badge');
    if (modoPomodoroActivo === "estudio") {
        alert("¡Felicidades! Completaste tu bloque de enfoque de 25 minutos. Tómate un descanso.");
        modoPomodoroActivo = "descanso";
        tiempoRestante = 5 * 60; // 5 minutos de descanso corto
        if (badge) {
            badge.style.background = 'var(--success)';
            badge.style.boxShadow = '0 0 15px var(--success)';
            badge.innerText = "☕ TIEMPO DE DESCANSO";
        }
    } else {
        alert("El tiempo de descanso terminó. ¡Listo para enfocar de nuevo!");
        modoPomodoroActivo = "estudio";
        tiempoRestante = 25 * 60;
        if (badge) {
            badge.style.background = 'var(--error)';
            badge.style.boxShadow = '0 0 15px var(--error)';
            badge.innerText = "⚡ MODO ENFOQUE ACTIVO";
        }
    }
    actualizarDisplayPomodoro();
    controlarPomodoro('start');
}

function cerrarModoEnfoque() {
    if (confirm("¿Estás seguro de que deseas salir? El temporizador se detendrá.")) {
        clearInterval(pomodoroIntervalo);
        pomodoroIntervalo = null;
        const contenedor = document.getElementById('pomodoro-focus-container');
        if (contenedor) contenedor.style.display = 'none';
    }
}

function analizarPrioridades() {
    const content = document.getElementById('ai-content');
    const scanner = document.querySelector('.ai-scanner-bar, .scanner-line');

    if (scanner) scanner.style.display = 'block';
    if (content) content.innerHTML = '<div class="loading-text" style="color:var(--accent); font-weight:700;">Ejecutando escaneo predictivo avanzado...</div>';

    setTimeout(() => {
        if (scanner) scanner.style.display = 'none';

        const tarjetas = Array.from(document.querySelectorAll('.tarea-card'));
        if (tarjetas.length === 0) {
            if (content) content.innerHTML = '<div style="font-size:0.85rem; opacity:0.7;">No hay tareas pendientes cargadas en el tablero actual.</div>';
            return;
        }

        let urgentesCriticas = [];
        let normales = [];
        let completadas = 0;
        let countImportantes = 0;
        const hoy = new Date();
        hoy.setHours(0,0,0,0);

        tarjetas.forEach(t => {
            const materia = t.querySelector('.materia-tag')?.innerText.trim() || 'S/M';
            const tema = t.querySelector('.tema-title')?.innerText.trim() || 'Sin título';
            const metaTexto = t.querySelector('.meta-data')?.innerText || '';
            const statusIcon = t.querySelector('.status-icon')?.innerText.trim() || '';

            if (statusIcon === '✅' || statusIcon === '✓') {
                completadas++;
                return;
            }

            let diasParaEntrega = 999;
            const regexFecha = /(\d{4})-(\d{2})-(\d{2})|(\d{2})\/(\d{2})\/(\d{4})/;
            const match = metaTexto.match(regexFecha);

            if (match) {
                let fechaTarea;
                if (match[1]) {
                    fechaTarea = new Date(match[1], match[2] - 1, match[3]);
                } else {
                    fechaTarea = new Date(match[6], match[5] - 1, match[4]);
                }
                fechaTarea.setHours(0,0,0,0);
                const diferenciaTiempo = fechaTarea.getTime() - hoy.getTime();
                diasParaEntrega = Math.ceil(diferenciaTiempo / (1000 * 60 * 60 * 24));
            }

            const esEstrella = t.innerText.includes('★') || metaTexto.toLowerCase().includes('examen');
            if (esEstrella) countImportantes++;
            
            const infoMision = { tema, materia, dias: diasParaEntrega, urgente: esEstrella, estado: statusIcon || '⭕' };

            if (diasParaEntrega <= 2 || esEstrella) {
                urgentesCriticas.push(infoMision);
            } else {
                normales.push(infoMision);
            }
        });

        const totalTareas = tarjetas.length;
        const pendientes = Math.max(0, totalTareas - completadas);
        let informe = totalTareas === 0 
            ? 'No hay tareas. Agrega una nueva para empezar.' 
            : `Tienes <strong>${totalTareas}</strong> tareas, <strong>${pendientes}</strong> pendientes y <strong>${completadas}</strong> completas. `;

        if (countImportantes > 0) {
            informe += `Hay <strong>${countImportantes}</strong> tareas prioritarias con ★.`;
        }

        let htmlResultado = `
            <div style="animation: fadeIn 0.5s ease; padding: 5px 2px; font-size:0.85rem; text-align:left; line-height:1.4;">
                <div style="margin-bottom: 12px;">
                    <h4 style="color: var(--accent); margin: 0 0 4px 0; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 700;">Métricas de Carga</h4>
                    <p style="margin: 0; font-size: 0.82rem; color: rgba(255,255,255,0.85);">${informe}</p>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 15px;">
                    <div style="background: rgba(56, 189, 248, 0.1); padding: 8px; border-radius: 10px; color: #a8d8ff; font-size: 0.75rem; border: 1px solid rgba(56, 189, 248, 0.15); text-align: center;">
                        Globales<br><strong style="font-size: 0.95rem;">${totalTareas}</strong>
                    </div>
                    <div style="background: rgba(255, 71, 87, 0.1); padding: 8px; border-radius: 10px; color: #ffa8b8; font-size: 0.75rem; border: 1px solid rgba(255, 71, 87, 0.15); text-align: center;">
                        Pendientes<br><strong style="font-size: 0.95rem;">${pendientes}</strong>
                    </div>
                </div>
        `;
        
        if (urgentesCriticas.length > 0) {
            htmlResultado += `<p style="color:var(--error); font-weight:800; margin-bottom:10px; font-size:0.8rem; letter-spacing:0.5px;">⚠️ DETECCION CRÍTICA (Radar IA):</p>`;
            urgentesCriticas.forEach(m => {
                let textPlazo = m.dias < 0 ? "VENCIDA" : (m.dias === 0 ? "¡ENTREGA HOY!" : `Resta: ${m.dias} día(s)`);
                htmlResultado += `
                    <div style="background:rgba(255,71,87,0.06); border:1px solid rgba(255,71,87,0.15); padding:10px; border-radius:10px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; gap:10px;">
                        <div style="min-width:0; flex:1;">
                            <span style="color:#fff; font-weight:700;">[${m.materia}]</span> ${m.tema}<br>
                            <span style="color:var(--error); font-weight:800; font-size:0.75rem;">⚡ PLAZO: ${textPlazo}</span>
                        </div>
                        <button onclick="activarModoEnfoque('${m.tema.replace(/'/g, "\\'")}', '${m.materia.replace(/'/g, "\\'")}')" 
                                style="background:var(--accent); color:#0f172a; border:none; padding:6px 12px; border-radius:8px; font-size:0.7rem; font-weight:800; cursor:pointer; flex-shrink:0; transition: transform 0.2s;">
                            🎯 FOCUS
                        </button>
                    </div>`;
            });
        } else {
            htmlResultado += `
                <p style="color:var(--success); font-weight:800; margin-bottom:6px;">✅ DIAGNÓSTICO ESTABLE:</p>
                <p style="color:var(--text-muted); font-size:0.8rem; margin-bottom:12px;">No detecté exámenes ni entregas colapsadas a corto plazo. ¡Buen ritmo!</p>
            `;
        }

        if (normales.length > 0) {
            htmlResultado += `<p style="color:var(--accent); font-weight:800; margin-top:12px; margin-bottom:6px; font-size:0.8rem;">📚 PLANIFICACIÓN SECUNDARIA:</p>`;
            normales.slice(0, 3).forEach(m => {
                htmlResultado += `
                    <div style="background: rgba(255,255,255,0.03); padding: 8px 10px; border-radius: 8px; margin-bottom: 4px; font-size: 0.8rem; display:flex; justify-content:space-between;">
                        <span style="color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:70%;">• <strong>${m.materia}:</strong> ${m.tema}</span>
                        <span style="color:var(--accent); font-size:0.75rem;">En ${m.dias}d</span>
                    </div>`;
            });
            if (normales.length > 3) {
                htmlResultado += `<p style="margin-top: 6px; font-size: 0.72rem; color: var(--text-muted); text-align:right;">+${normales.length - 3} tareas más mapeadas</p>`;
            }
        }

        htmlResultado += `</div>`;
        if (content) content.innerHTML = htmlResultado;
    }, 1000);
}

function toggleAssistant() {
    const panel = document.getElementById('ai-panel');
    const helpModal = document.getElementById('help-modal');
    if (!panel) return;
    
    if (panel.style.display === 'none' || panel.style.display === '') {
        if (helpModal) helpModal.style.display = 'none';
        
        panel.style.display = 'block';
        panel.classList.add('animate-in'); 

        fetchAssistantData();
    } else {
        panel.style.display = 'none';
    }
}

async function fetchAssistantData() {
    const content = document.getElementById('ai-content');
    if (content) {
        content.innerHTML = '<p style="font-size:0.85rem; opacity:0.8;">Consultando heurística en la nube...</p><div class="loader"></div>';
    }
    
    try {
        const response = await fetch('/ai_analisis');
        if (!response.ok) throw new Error('Error de respuesta de servidor local');
        
        const data = await response.json();
        
        analizarPrioridades(); 
    } catch (error) {
        console.warn("[Radar Local Operativo] Backend sin endpoint /ai_analisis, ejecutando escáner de cliente:", error);
       
        analizarPrioridades();
    }
}

function toggleHelp() {
    const helpModal = document.getElementById('help-modal');
    const panel = document.getElementById('ai-panel');
    if (!helpModal) return;

    if (helpModal.style.display === 'none' || helpModal.style.display === '') {
        if (panel) panel.style.display = 'none';
        helpModal.style.display = 'block';
    } else {
        helpModal.style.display = 'none';
    }
}

function toggleMenu(event) {
    if (event) event.stopPropagation();
    const menu = document.getElementById('dropdown-perfil');
    if (menu) menu.classList.toggle('active');
}

function abrirModalImagen() {
    const modal = document.getElementById('modalImagen');
    if (modal) modal.style.display = 'flex';
    
    const menu = document.getElementById('dropdown-perfil');
    if (menu) menu.classList.remove('active');
}

function cerrarModal() {
    const modal = document.getElementById('modalImagen');
    if (modal) modal.style.display = 'none';
}

document.addEventListener("DOMContentLoaded", function() {

    const panel = document.getElementById('ai-panel');
    if (panel) panel.style.display = 'none';

    const helpCard = document.querySelector('.help-card') || document.getElementById('help-modal');
    if (helpCard && !document.getElementById('guia-maestra-extendida')) {
        const extensionAyuda = document.createElement('div');
        extensionAyuda.id = "guia-maestra-extendida";
        extensionAyuda.style.marginTop = "20px";
        extensionAyuda.style.paddingTop = "15px";
        extensionAyuda.style.borderTop = "1px solid rgba(255, 255, 255, 0.1)";
        extensionAyuda.style.textAlign = "left";
        
        extensionAyuda.innerHTML = `
            <h3 style="color: var(--accent); font-size: 1.1rem; margin-bottom: 15px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;">
                 Manual del Sistema Maestro
            </h3>
            
            <div class="ayuda-seccion" style="margin-bottom: 18px; background: rgba(255,255,255,0.02); padding: 12px; border-radius: 10px; border-left: 3px solid var(--accent);">
                <h4 style="margin: 0 0 8px 0; font-size: 0.9rem; color: #fff; font-weight: 700;">
                     Sistema de Niveles y Rachas
                </h4>
                <ul style="margin: 0; padding-left: 18px; font-size: 0.82rem; color: var(--text-muted); line-height: 1.5;">
                    <li><strong>Cálculo de XP:</strong> Cada tarea ordinaria completada otorga <span style="color:#2ed573;">+10 XP</span>. Si es un examen o actividad importante, obtienes <span style="color:#2ed573;">+30 XP</span>.</li>
                    <li><strong>Multiplicador de Racha:</strong> Mantener tu fuego activo días seguidos incrementa tu rango visible en el perfil.</li>
                    <li><strong>Evolución de Rango:</strong> Superar el nivel 5 desbloquea un aura legendaria animada en tu avatar.</li>
                </ul>
            </div>

            <div class="ayuda-seccion" style="margin-bottom: 18px; background: rgba(255,255,255,0.02); padding: 12px; border-radius: 10px; border-left: 3px solid var(--error);">
                <h4 style="margin: 0 0 8px 0; font-size: 0.9rem; color: #fff; font-weight: 700;">
                     Papelera de Eco-Recuperación
                </h4>
                <p style="margin: 0; font-size: 0.82rem; color: var(--text-muted); line-height: 1.5;">
                    Al eliminar una tarea, esta pasa a un estado de suspensión por un plazo estricto de <strong>48 horas</strong>. Puedes restaurarla con su XP intacto. Pasado el límite, el servidor purga el registro permanentemente.
                </p>
            </div>
        `;
        helpCard.appendChild(extensionAyuda);
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const panel = document.getElementById('ai-panel');
        const helpModal = document.getElementById('help-modal');
        if (panel) panel.style.display = 'none';
        if (helpModal) helpModal.style.display = 'none';
    }
});

document.addEventListener('click', function(event) {

    const menu = document.getElementById('dropdown-perfil');
    if (menu && !event.target.closest('#dropdown-perfil') && !event.target.closest('.profile-main-circle')) {
        menu.classList.remove('active');
    }

    const modalAyuda = document.getElementById('help-modal');
    const containerAyuda = document.getElementById('help-container-root');
    if (modalAyuda && modalAyuda.style.display === 'block' && containerAyuda && !containerAyuda.contains(event.target)) {
        modalAyuda.style.display = 'none';
    }
});