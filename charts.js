// Login Failure Trend Chart
const ctx1 = document.getElementById("loginTrendChart");

if (ctx1) {
    new Chart(ctx1, {
        type: "line",
        data: {
            labels: login_labels,
            datasets: [{
                label: "Failed Login Attempts",
                data: login_values,
                borderWidth: 2,
                borderColor: "#38bdf8",
                backgroundColor: "rgba(56, 189, 248, 0.2)",
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { labels: { color: "#e2e8f0" } }
            },
            scales: {
                x: { ticks: { color: "#e2e8f0" } },
                y: { ticks: { color: "#e2e8f0" } }
            }
        }
    });
}

// Alert Severity Distribution
const ctx2 = document.getElementById("alertPieChart");

if (ctx2) {
    new Chart(ctx2, {
        type: "pie",
        data: {
            labels: ["Critical", "Warning", "Low"],
            datasets: [{
                data: severity_counts,
                backgroundColor: [
                    "rgba(239,68,68,0.8)",
                    "rgba(234,179,8,0.8)",
                    "rgba(34,197,94,0.8)"
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { labels: { color: "#e2e8f0" } }
            }
        }
    });
}
