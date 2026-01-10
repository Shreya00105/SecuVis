// Refresh Data Button
document.addEventListener("DOMContentLoaded", () => {
    const refreshBtn = document.getElementById("refreshData");

    if (refreshBtn) {
        refreshBtn.addEventListener("click", async () => {
            refreshBtn.innerText = "Refreshing...";
            
            const res = await fetch("/refresh-data");
            const msg = await res.json();

            alert("Data Updated: " + msg.status);
            refreshBtn.innerText = "Refresh Data";
        });
    }
});

// Simple Table Row Animation
const rows = document.querySelectorAll(".alert-row-critical, .alert-row-warning");

rows.forEach(row => {
    row.style.transition = "0.3s";
    row.addEventListener("mouseover", () => { row.style.transform = "scale(1.01)"; });
    row.addEventListener("mouseout", () => { row.style.transform = "scale(1.0)"; });
});
