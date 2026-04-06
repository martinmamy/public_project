// ==============================
// SEND TIPS (PROBLEM & ANSWER)
// ==============================
document.addEventListener("DOMContentLoaded", () => {
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  function sendTip(url, input, badge) {
    const amount = parseFloat(input.value);
    if (isNaN(amount) || amount <= 0) {
      alert("Enter a valid tip amount");
      return;
    }

    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken
      },
      body: JSON.stringify({ amount })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        badge.innerHTML = `<i class="fas fa-coins"></i> ${data.tips_received}`;
        input.value = "";
      } else {
        alert(data.error || "Tip failed");
      }
    })
    .catch(err => console.error("Tip request failed:", err));
  }

  document.addEventListener("click", (e) => {
    // Answer tip
    const answerBtn = e.target.closest(".send-tip-btn");
    if (answerBtn) {
      const container = answerBtn.closest(".d-flex");
      const input = container.querySelector(".tip-amount");
      const badge = container.querySelector(".badge");
      sendTip(`/answers/${answerBtn.dataset.id}/tip/`, input, badge);
    }

    // Problem tip
    const problemBtn = e.target.closest(".send-problem-tip-btn");
    if (problemBtn) {
      const container = problemBtn.closest(".d-flex");
      const input = container.querySelector(".problem-tip-amount");
      const badge = container.querySelector(".badge");
      sendTip(`/problems/${problemBtn.dataset.id}/tip/`, input, badge);
    }
  });
});