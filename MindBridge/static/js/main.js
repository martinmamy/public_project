// main.js

document.addEventListener("DOMContentLoaded", function () {

    // =========================
    // Load Trending Problems
    // =========================
    async function loadTrendingProblems() {
        const sidebar = document.getElementById("trending-sidebar");
        if (!sidebar) return;

        try {
            const response = await fetch("/api/trending-problems/");
            const problems = await response.json();

            sidebar.innerHTML = "";

            problems.forEach(problem => {
                const li = document.createElement("li");
                li.classList.add("list-group-item");

                li.innerHTML = `
                    <a href="/problems/${problem.id}/" 
                       class="text-decoration-none text-dark">
                       ${problem.title}
                    </a>
                `;

                sidebar.appendChild(li);
            });

        } catch (error) {
            console.error("Error loading trending problems:", error);
        }
    }


    // =========================
    // Load Suggested Experts
    // =========================
    async function loadSuggestedExperts() {

        const sidebar = document.getElementById("suggested-users-sidebar");
        if (!sidebar) return;

        try {

            const response = await fetch("/api/suggested-experts/");
            const experts = await response.json();

            sidebar.innerHTML = "";

            experts.forEach(expert => {

                const li = document.createElement("li");
                li.classList.add("list-group-item", "d-flex", "align-items-center");

                li.innerHTML = `
                    <img src="${expert.avatar}" 
                         alt="${expert.name}"
                         class="rounded-circle me-2"
                         width="35"
                         height="35">

                    <a href="/profile/${expert.id}/" 
                       class="text-decoration-none text-dark">
                       ${expert.name}
                    </a>
                `;

                sidebar.appendChild(li);

            });

        } catch (error) {
            console.error("Error loading experts:", error);
        }
    }


    // =========================
    // Feed Interactions
    // =========================
    document.querySelectorAll(".feed-card").forEach((card) => {

        const likeBtn = card.querySelector(".btn-primary");
        const commentBtn = card.querySelector(".btn-outline-secondary:nth-child(2)");
        const shareBtn = card.querySelector(".btn-outline-secondary:nth-child(3)");

        // Like button
        if (likeBtn) {

            likeBtn.addEventListener("click", () => {

                likeBtn.classList.toggle("btn-primary");
                likeBtn.classList.toggle("btn-success");

                likeBtn.innerHTML = likeBtn.classList.contains("btn-success")
                    ? '<i class="fas fa-thumbs-up"></i> Liked'
                    : '<i class="fas fa-thumbs-up"></i> Like';

            });

        }

        // Comment
        if (commentBtn) {
            commentBtn.addEventListener("click", () => {
                alert("Comment feature coming soon!");
            });
        }

        // Share
        if (shareBtn) {
            shareBtn.addEventListener("click", () => {
                alert("Share feature coming soon!");
            });
        }

    });


    // =========================
    // Navbar Shadow on Scroll
    // =========================
    const navbar = document.querySelector(".navbar");

    window.addEventListener("scroll", () => {

        if (!navbar) return;

        if (window.scrollY > 20) {
            navbar.classList.add("shadow-lg");
        } else {
            navbar.classList.remove("shadow-lg");
        }

    });


    // =========================
    // Load dynamic data
    // =========================
    loadTrendingProblems();
    loadSuggestedExperts();

});