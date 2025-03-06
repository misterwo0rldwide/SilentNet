const urlParams = new URLSearchParams(window.location.search);
const passwordIncorrect = urlParams.get('password_incorrect');

if (passwordIncorrect === 'true') {
    document.getElementById('error-message').style.display = 'block';
}