document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("dashboardChart");
    if (!canvas || typeof Chart === "undefined") return;

    new Chart(canvas, {
        type: "line",
        data: {
            labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            datasets: [{
                label: "Spending",
                data: [0, 0, 0, 0, 0, 0, 0],
                borderWidth: 2,
                tension: 0.4,
                pointRadius: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: "#777e90", font: { size: 9 } } },
                y: { beginAtZero: true, grid: { color: "rgba(255,255,255,.05)" }, ticks: { color: "#777e90", font: { size: 9 } } }
            }
        }
    });
});