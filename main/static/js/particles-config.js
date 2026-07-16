// static/js/particles-config.js - Улучшенная версия
document.addEventListener('DOMContentLoaded', function() {
    if (typeof tsParticles !== 'undefined') {
        tsParticles.load('tsparticles', {
            fpsLimit: 30,
            interactivity: {
                events: {
                    onHover: {
                        enable: true,
                        mode: 'attract' // Частицы притягиваются к курсору
                    },
                    resize: true
                },
                modes: {
                    attract: {
                        distance: 200,
                        duration: 0.4,
                        factor: 1.5 // Усилил притяжение
                    }
                }
            },
            particles: {
                color: {
                    value: '#ffffff'
                },
                links: {
                    color: '#ffffff',
                    distance: 180, // Увеличил расстояние связей
                    enable: true,
                    opacity: 0.35, // Ярче связи
                    width: 1.5 // Толще линии
                },
                move: {
                    enable: true,
                    speed: 0.4, // Чуть быстрее
                    direction: 'none',
                    random: true,
                    straight: false,
                    outModes: {
                        default: 'bounce'
                    }
                },
                number: {
                    density: {
                        enable: true,
                        area: 1000 // Плотнее
                    },
                    value: 40 // Больше частиц
                },
                opacity: {
                    value: 0.4, // Ярче
                    random: true,
                    anim: {
                        enable: false
                    }
                },
                shape: {
                    type: 'circle'
                },
                size: {
                    value: { min: 2, max: 5 }, // Крупнее
                    random: true,
                    anim: {
                        enable: false
                    }
                }
            },
            detectRetina: true
        });
    }
});