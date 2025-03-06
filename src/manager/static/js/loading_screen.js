function manualConnect() {
    fetch('/manual-connect')
        .then(response => response.json())
        .then(data => {
            if (data.status === true) {
                alert("Connected successfully!");
                window.location.href = '/';
            } else {
                alert("Connection attempt failed. Please try again.");
            }
        });
}

function exitProgram() {
    window.location.href = "exit";
}