let timeLeft = 10;
const countdownElement = document.getElementById('countdown');
const redirectButton = document.getElementById('redirectButton');

const redirectToLoadingScreen = () => {
    window.location.href = "/loading";
};

const timer = setInterval(() => {
    timeLeft--;
    countdownElement.textContent = timeLeft;

    if (timeLeft <= 0) {
        clearInterval(timer);
        redirectToLoadingScreen();
    }
}, 1000);

redirectButton.addEventListener('click', (e) => {
    e.preventDefault();
    clearInterval(timer);
    redirectToLoadingScreen();
});