function donate(amount) {
    alert("Proceeding to donate ₹" + amount);
    window.location.href = "donate.html?amount=" + amount;
}

fetch("http://127.0.0.1:5000/donate", {
    method: "POST",
    headers: {
        "Content-Type": "application/json"
    },
    body: JSON.stringify({ amount: amount })
});