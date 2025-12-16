AOS.init({
    duration: 800,
    once: true,
    offset: 100
});

function toggleMenu() {
    const nav = document.getElementById('main-nav');
    nav.classList.toggle('active');
}

document.addEventListener('click', function(event) {
    const nav = document.getElementById('main-nav');
    const menuBtn = document.querySelector('.mobile-menu-btn');
    
    if (!nav.contains(event.target) && !menuBtn.contains(event.target)) {
        nav.classList.remove('active');
    }
});

window.addEventListener('scroll', function() {
    const header = document.getElementById('header');
    const backToTop = document.getElementById('backToTop');
    
    if (window.scrollY > 100) {
        header.classList.add('scrolled');
        backToTop.classList.add('visible');
    } else {
        header.classList.remove('scrolled');
        backToTop.classList.remove('visible');
    }
});

document.getElementById('backToTop').addEventListener('click', function() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    document.getElementById('currentYear').textContent = new Date().getFullYear();
});

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
        if (this.getAttribute('href') === '#' || this.type === 'submit') {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        }
    });
});

function updateCartUI(responseData) {
    if (responseData && responseData.cart_count !== undefined) {
        const badge = document.getElementById('anonymousCartCount');
        if (badge) {
            const count = responseData.cart_count;
            if (count > 0) {
                badge.style.display = 'inline-block';
                badge.innerHTML = ''; 
                badge.classList.add('pulse');
                setTimeout(() => badge.classList.remove('pulse'), 500);
            } else {
                badge.style.display = 'none';
            }
        }
    }
}

function refreshCartCount() {
    fetch('/anonymous-cart/items/', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateCartUI({ cart_count: data.count });
        }
    })
    .catch(error => console.error('Error refreshing cart:', error));
}

document.addEventListener('DOMContentLoaded', function() {
    refreshCartCount();
    
    document.addEventListener('cartUpdated', function(e) {
        updateCartUI(e.detail);
    });
});

function triggerCartUpdate(data) {
    document.dispatchEvent(new CustomEvent('cartUpdated', { detail: data }));
}

