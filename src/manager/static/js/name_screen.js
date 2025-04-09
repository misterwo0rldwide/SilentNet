function showTooltip(text) {
    const tooltip = document.getElementById('tooltip');
    tooltip.textContent = text;
    tooltip.style.display = 'block';
}

function hideTooltip() {
    const tooltip = document.getElementById('tooltip');
    tooltip.style.display = 'none';
}

function deleteName(name) {
    if (confirm(`Are you sure you want to delete "${name}"?`)) {
        fetch('/delete_client', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: name })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Find and remove the name card from the DOM
                const cards = document.querySelectorAll('.name-card');
                cards.forEach(card => {
                    if (card.textContent.includes(name)) {
                        card.remove();
                    }
                });
            } else {
                alert('Failed to delete: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while deleting');
        });
    }
}