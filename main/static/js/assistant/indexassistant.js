// static/js/assistant/index.js

// Проверяем загрузку всех данных
document.addEventListener('DOMContentLoaded', function() {
  // Ждем загрузки всех скриптов данных
  const checkData = () => {
    if (typeof window.ASSISTANT_URLS !== 'undefined') {
      // Все данные загружены, инициализируем помощник
      new SmartAssistant();
    } else {
      // Ждем еще немного
      setTimeout(checkData, 100);
    }
  };

  checkData();
});