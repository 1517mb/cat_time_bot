/**
 * Copies the given text to the user's clipboard using the `copyToClipboard`
 * function from the `clip.js` script.
 *
 * @param {string} elementId - The id of the input element to copy from
 */
function copyToClipboard(elementId) {
    let inputElement;
    if (elementId === 'password') {
        inputElement = document.getElementById('password');
    } else {
        inputElement = document.querySelector(`input[value='${elementId}']`);
    }
    navigator.clipboard.writeText(inputElement.value).then(function() {
        showNotification("Пароль скопирован в буфер обмена!");
    }).catch(function(err) {
        showNotification("Не удалось скопировать пароль: " + err);
    });
}

/**
 * Displays a notification with the specified message at the top right corner of the page.
 * The notification includes a delete button to manually close it and automatically
 * disappears after 5 seconds.
 *
 * @param {string} message - The message to display within the notification.
 */
function showNotification(message) {
    const notification = document.createElement("div");
    notification.className = "notification is-success is-light";
    notification.innerHTML = `
        <button class="delete"></button>
        ${message}
    `;

    const notificationContainer = document.getElementById("notification-container");
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
