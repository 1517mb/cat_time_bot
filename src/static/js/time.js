
document.addEventListener("DOMContentLoaded", () => {
    /**
     * Updates the Moscow time element with the current Moscow time.
     *
     * This function gets the current date and time, formats it according to the
     * Russian locale and the Europe/Moscow time zone, and sets the text content
     * of the element with the id "moscow-time" to the formatted time.
     */
    function updateMoscowTime() {
        const moscowTimeElement = document.getElementById("moscow-time");
        const now = new Date();
        const options = { timeZone: 'Europe/Moscow', hour: '2-digit', minute: '2-digit', second: '2-digit' };
        const moscowTime = now.toLocaleTimeString('ru-RU', options);
        moscowTimeElement.textContent = `Московское время: ${moscowTime}`;
    }

    // Обновляем время каждую секунду
    setInterval(updateMoscowTime, 1000);

    // Инициализация времени при загрузке страницы
    updateMoscowTime();
});
