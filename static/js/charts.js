document.addEventListener("DOMContentLoaded", () => {
    if (typeof Chart === "undefined") return;

    const weekly = document.getElementById("weeklyChart");
    if (weekly) {
        new Chart(weekly, {
            type: "bar",
            data: {
                labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                datasets: [{
                    label: "Weekly Spending",
                    data: [0, 0, 0, 0, 0, 0, 0],
                    borderRadius: 6
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
    }

    const category = document.getElementById("categoryChart");
    if (category) {
        new Chart(category, {
            type: "doughnut",
            data: {
                labels: ["Food", "Travel", "Shopping", "Bills", "Other"],
                datasets: [{
                    data: [1, 1, 1, 1, 1],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "68%",
                plugins: { legend: { position: "bottom", labels: { color: "#9da3b5", font: { size: 9 }, padding: 15 } } }
            }
        });
    }
});