// static/js/particles-config.js - Элегантная версия
document.addEventListener('DOMContentLoaded', function() {
    if (typeof tsParticles !== 'undefined') {
        tsParticles.load('tsparticles', {
            fpsLimit: 60,
            interactivity: {
                events: {
                    onHover: {
                        enable: true,
                        mode: 'grab' // Мягкое притяжение при наведении
                    },
                    resize: true
                },
                modes: {
                    grab: {
                        distance: 150,
                        links: {
                            opacity: 0.3
                        }
                    }
                }
            },
            particles: {
                color: {
                    value: '#c0c0c0' // Серебристый оттенок вместо белого
                },
                links: {
                    color: '#c0c0c0',
                    distance: 120,
                    enable: true,
                    opacity: 0.15, // Едва заметные связи
                    width: 0.8
                },
                move: {
                    enable: true,
                    speed: 0.3,
                    direction: 'none',
                    random: false, // Убираем случайность движения
                    straight: false,
                    outModes: {
                        default: 'out' // Частицы плавно выходят за края
                    },
                    drift: 0 // Убираем дрейф
                },
                number: {
                    density: {
                        enable: true,
                        area: 1200
                    },
                    value: 30 // Умеренное количество
                },
                opacity: {
                    value: 0.25,
                    random: true,
                    anim: {
                        enable: true,
                        speed: 0.5,
                        minimumValue: 0.1,
                        sync: false
                    }
                },
                shape: {
                    type: 'circle'
                },
                size: {
                    value: { min: 1, max: 3 },
                    random: true,
                    anim: {
                        enable: true,
                        speed: 0.5,
                        minimumValue: 0.5,
                        sync: false
                    }
                }
            },
            detectRetina: true,
            background: {
                color: 'transparent' // Прозрачный фон
            }
        });
    }
});