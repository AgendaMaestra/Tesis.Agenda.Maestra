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