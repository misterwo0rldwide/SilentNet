function updateSliderValue(sliderId, valueId) {
    const slider = document.getElementById(sliderId);
    const valueDisplay = document.getElementById(valueId);
    valueDisplay.textContent = slider.value;
}