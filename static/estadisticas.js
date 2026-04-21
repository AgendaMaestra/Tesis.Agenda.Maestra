document.addEventListener("DOMContentLoaded", function () {

    const dataElement = document.getElementById("stats-data");
    if (!dataElement) return;

    const tareasHechas = parseInt(dataElement.dataset.hechas) || 0;
    const tareasPendientes = parseInt(dataElement.dataset.pendientes) || 0;

    const ctx = document.getElementById("chart");
    if (!ctx) return;

    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Completadas", "Pendientes"],
            datasets: [{
                data: [tareasHechas, tareasPendientes],
                backgroundColor: [
                    "#2ed573",
                    "#ff4757"
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: {
                        color: "#ffffff"
                    }
                }
            }
        }
    });

});

function toggleAssistant() {
    const panel = document.getElementById('ai-panel');
    if (panel.style.display === 'none' || panel.style.display === '') {
        panel.style.display = 'block';
    } else {
        panel.style.display = 'none';
    }
}

function toggleHelp() {
    const modal = document.getElementById('help-modal');
    if (modal.style.display === 'none' || modal.style.display === '') {
        modal.style.display = 'block';
    } else {
        modal.style.display = 'none';
    }
}