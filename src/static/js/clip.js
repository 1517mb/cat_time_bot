function copyToClipboard(elementId) {
    const inputElement = document.getElementById(elementId);
    if (!inputElement) {
        showNotification("Элемент для копирования не найден!");
        return;
    }

    navigator.clipboard.writeText(inputElement.value).then(function() {
        showNotification("Пароль скопирован в буфер обмена!");
    }).catch(function(err) {
        showNotification("Не удалось скопировать пароль: " + err);
    });
}

function showNotification(message) {
    const notificationContainer = document.getElementById("notification-container");
    if (!notificationContainer) {
        console.error("Контейнер для уведомлений не найден!");
        return;
    }

    const notification = document.createElement("div");
    notification.className = "notification is-success is-light";
    notification.innerHTML = `
        <button class="delete"></button>
        ${message}
    `;

    notificationContainer.appendChild(notification);

    // Adding a handler to close the alert
    const deleteButton = notification.querySelector(".delete");
    deleteButton.addEventListener("click", () => {
        notification.parentNode.removeChild(notification);
    });

    // We delete the notification after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

document.addEventListener("DOMContentLoaded", () => {
    (document.querySelectorAll(".notification .delete") || []).forEach(($delete) => {
        const $notification = $delete.parentNode;

        $delete.addEventListener("click", () => {
            $notification.parentNode.removeChild($notification);
        });
    });
});