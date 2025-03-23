document.addEventListener('DOMContentLoaded', () => {
    document.body.addEventListener('click', async (e) => {
      if (e.target.closest('.copy-button')) {
        const button = e.target.closest('.copy-button');
        const targetId = button.dataset.target;
        await copyToClipboard(targetId);
      }

      if (e.target.classList.contains('delete')) {
        e.target.closest('.notification').remove();
      }
    });
  });
  
  async function copyToClipboard(elementId) {
    try {
      const element = document.getElementById(elementId);
      
      if (!element) {
        showNotification("Элемент не найден!", 'is-danger');
        return;
      }
  
      const textToCopy = element.value 
        || element.textContent 
        || element.innerText;
  
      await navigator.clipboard.writeText(textToCopy);
      showNotification("Скопировано в буфер!", 'is-success');
      
    } catch (err) {
      console.error('Ошибка копирования:', err);
      showNotification("Ошибка копирования", 'is-danger');
    }
  }
  
  function showNotification(message, type = 'is-success') {
    const notificationContainer = document.getElementById("notification-container");
    if (!notificationContainer) {
      console.error('Контейнер для уведомлений не найден');
      return;
    }
  
    const notification = document.createElement('div');
    notification.className = `notification ${type} is-light`;
    notification.innerHTML = `
      <button class="delete"></button>
      ${message}
    `;
  
    notificationContainer.appendChild(notification);
    setTimeout(() => notification.remove(), 5000);
  }