document.addEventListener("DOMContentLoaded", function () {
  if (typeof AOS !== "undefined") {
    AOS.init({ duration: 600, once: !0, offset: 100 });
  }
  const currentPath = window.location.pathname;
  const categoryLinks = document.querySelectorAll(".category-link");
  categoryLinks.forEach((link) => {
    if (link.getAttribute("href") === currentPath) {
      link.classList.add("active");
    }
  });
  const commentSection = document.getElementById("comments");
  if (commentSection) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            console.log("Комментарии видны");
          }
        });
      },
      { threshold: 0.5 }
    );
    observer.observe(commentSection);
  }
  function calculateReadingTime() {
    const articleBody = document.querySelector(".article-body");
    if (articleBody) {
      const text = articleBody.textContent || articleBody.innerText;
      const wordCount = text.trim().split(/\s+/).length;
      const readingTime = Math.ceil(wordCount / 200);
      const readingTimeElement = document.querySelector(".reading-time");
      if (readingTimeElement) {
        readingTimeElement.textContent = `${readingTime} мин. чтения`;
      }
    }
  }
  calculateReadingTime();
  const shareButtons = document.querySelectorAll(".share-btn");
  shareButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      const url = window.location.href;
      if (navigator.clipboard) {
        navigator.clipboard
          .writeText(url)
          .then(() => {
            showNotification("Ссылка скопирована в буфер обмена!", "success");
          })
          .catch((err) => {
            console.error("Ошибка копирования:", err);
            showNotification("Не удалось скопировать ссылку", "error");
          });
      } else {
        const tempInput = document.createElement("input");
        tempInput.value = url;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand("copy");
        document.body.removeChild(tempInput);
        showNotification("Ссылка скопирована!", "success");
      }
    });
  });
  function showNotification(message, type) {
    const notification = document.createElement("div");
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
            <i class="fas fa-${
              type === "success" ? "check-circle" : "exclamation-circle"
            }"></i>
            <span>${message}</span>
        `;
    document.body.appendChild(notification);
    setTimeout(() => {
      notification.classList.add("show");
    }, 10);
    setTimeout(() => {
      notification.classList.remove("show");
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 300);
    }, 3000);
  }
  if (!document.querySelector("#notification-styles")) {
    const style = document.createElement("style");
    style.id = "notification-styles";
    style.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 1rem 1.5rem;
                border-radius: 8px;
                background: white;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                display: flex;
                align-items: center;
                gap: 0.75rem;
                z-index: 9999;
                transform: translateX(100%);
                opacity: 0;
                transition: transform 0.3s ease, opacity 0.3s ease;
                max-width: 400px;
            }
            
            .notification.show {
                transform: translateX(0);
                opacity: 1;
            }
            
            .notification-success {
                border-left: 4px solid #10b981;
            }
            
            .notification-success i {
                color: #10b981;
            }
            
            .notification-error {
                border-left: 4px solid #ef4444;
            }
            
            .notification-error i {
                color: #ef4444;
            }
            
            @media (max-width: 768px) {
                .notification {
                    left: 20px;
                    right: 20px;
                    max-width: none;
                }
            }
        `;
    document.head.appendChild(style);
  }
  if ("IntersectionObserver" in window) {
    const lazyImages = document.querySelectorAll('img[loading="lazy"]');
    const imageObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src || img.src;
          img.classList.add("loaded");
          imageObserver.unobserve(img);
        }
      });
    });
    lazyImages.forEach((img) => imageObserver.observe(img));
  }
});
window.BlogUtils = {
  calculateReadingTime: function () {
    const articleBody = document.querySelector(".article-body");
    if (articleBody) {
      const text = articleBody.textContent || articleBody.innerText;
      return Math.ceil(text.trim().split(/\s+/).length / 200);
    }
    return 0;
  },
  scrollToComments: function () {
    const commentsSection = document.getElementById("comments");
    if (commentsSection) {
      commentsSection.scrollIntoView({ behavior: "smooth" });
    }
  },
  toggleSidebar: function () {
    const sidebar = document.querySelector(".blog-sidebar");
    if (sidebar) {
      sidebar.classList.toggle("mobile-visible");
    }
  },
};

function toggleMenu() {
    const nav = document.getElementById("main-nav");
    if (nav) {
        const isActive = nav.classList.contains('active');
        console.log('Toggle menu. Current state:', isActive ? 'open' : 'closed');
        nav.classList.toggle('active');
        console.log('New state:', nav.classList.contains('active') ? 'open' : 'closed');
        
        if (!nav.classList.contains('active')) {
            nav.style.display = 'none';
        } else {
            nav.style.display = 'flex';
        }
    } else {
        console.error('Menu element #main-nav not found!');
    }
}