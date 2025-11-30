document.addEventListener('DOMContentLoaded', () => {
    document.body.addEventListener('click', async (e) => {
        const button = e.target.closest('.copy-button');
        if (button) {
            const targetId = button.dataset.target;
            await copyToClipboard(targetId, button);
        }
        if (e.target.classList.contains('delete')) {
            const notification = e.target.closest('.notification');
            if (notification) {
                closeNotification(notification);
            }
        }
    });
});
async function copyToClipboard(elementId, button) {
    try {
        const element = document.getElementById(elementId);
        
        if (!element) {
            showNotification("Элемент для копирования не найден!", 'is-danger');
            return;
        }
        const textToCopy = element.value || element.textContent || element.innerText;
        await navigator.clipboard.writeText(textToCopy);
        showNotification("Пароль успешно скопирован!", 'is-success');
        if (button) {
            animateButtonSuccess(button);
        }

    } catch (err) {
        console.error('Ошибка копирования:', err);
        showNotification("Не удалось скопировать пароль", 'is-danger');
    }
}
function animateButtonSuccess(button) {
    const iconSpan = button.querySelector('.icon i');
    if (!iconSpan) {
        button.classList.add('is-success');
        setTimeout(() => button.classList.remove('is-success'), 2000);
        return;
    }

    const originalClass = iconSpan.className;
    button.classList.add('is-success');
    iconSpan.className = 'fa-solid fa-check';
    setTimeout(() => {
        button.classList.remove('is-success');
        iconSpan.className = originalClass;
    }, 2000);
}

function showNotification(message, type = 'is-info') {
    const container = document.getElementById("notification-container");
    if (!container) return;

    let iconClass = 'fa-info-circle';
    if (type === 'is-success') iconClass = 'fa-circle-check';
    if (type === 'is-danger') iconClass = 'fa-circle-exclamation';

    const notification = document.createElement('div');
    notification.className = `notification ${type} notification-toast is-light`;
    
    notification.innerHTML = `
        <button class="delete"></button>
        <span class="icon-text">
            <span class="icon">
                <i class="fa-solid ${iconClass}"></i>
            </span>
            <span>${message}</span>
        </span>
    `;

    container.appendChild(notification);

    setTimeout(() => {
        closeNotification(notification);
    }, 3000);
}


function closeNotification(notification) {
    notification.classList.add('hide');
    notification.addEventListener('animationend', () => {
        notification.remove();
    });
}