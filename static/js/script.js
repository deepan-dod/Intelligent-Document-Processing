document.addEventListener("DOMContentLoaded", () => {
    const menu = document.getElementById("mobileMenu");
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");

    if (menu && sidebar && overlay) {
        menu.addEventListener("click", () => {
            sidebar.classList.toggle("open");
            overlay.classList.toggle("show");
        });
        overlay.addEventListener("click", () => {
            sidebar.classList.remove("open");
            overlay.classList.remove("show");
        });
    }

    const fileInput = document.getElementById("invoiceFile");
    const fileName = document.getElementById("fileName");
    if (fileInput && fileName) {
        fileInput.addEventListener("change", () => {
            fileName.textContent = fileInput.files.length
                ? "Selected: " + fileInput.files[0].name
                : "";
        });
    }

    document.querySelectorAll(".suggestion").forEach(button => {
        button.addEventListener("click", () => {
            const input = document.getElementById("chatInput");
            if (input) {
                input.value = button.textContent;
                input.focus();
            }
        });
    });

    const chatForm = document.getElementById("chatForm");
    if (chatForm) {
        chatForm.addEventListener("submit", e => {
            e.preventDefault();
            const input = document.getElementById("chatInput");
            const messages = document.getElementById("chatMessages");
            if (!input || !messages || !input.value.trim()) return;

            const text = input.value.trim();
            messages.insertAdjacentHTML("beforeend", `
                <div class="message user">
                    <div class="bubble">${escapeHtml(text)}</div>
                </div>
            `);

            input.value = "";
            messages.scrollTop = messages.scrollHeight;

            setTimeout(() => {
                messages.insertAdjacentHTML("beforeend", `
                    <div class="message assistant">
                        <div class="message-avatar">✦</div>
                        <div class="bubble">
                            Your AI assistant backend will be connected here. Once your expense data is available, I can answer this question using your actual spending history.
                        </div>
                    </div>
                `);
                messages.scrollTop = messages.scrollHeight;
            }, 500);
        });
    }

    const search = document.getElementById("invoiceSearch");
    const table = document.getElementById("invoiceTable");
    if (search && table) {
        search.addEventListener("input", () => {
            const term = search.value.toLowerCase();
            table.querySelectorAll("tbody tr").forEach(row => {
                row.style.display = row.textContent.toLowerCase().includes(term) ? "" : "none";
            });
        });
    }

    const status = document.getElementById("statusFilter");
    if (status && table) {
        status.addEventListener("change", () => {
            const value = status.value.toLowerCase();
            table.querySelectorAll("tbody tr").forEach(row => {
                const match = !value || row.textContent.toLowerCase().includes(value);
                row.style.display = match ? "" : "none";
            });
        });
    }
});

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}