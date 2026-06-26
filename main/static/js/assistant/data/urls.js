// static/js/assistant/data/urls.js

/**
 * Файл со всеми ссылками сайта
 *
 * Заполните все URL-адреса, которые используются на сайте.
 * Ключи используются в других файлах через {{URL_КЛЮЧ}}
 *
 * Формат: КЛЮЧ: 'URL'
 */

const ASSISTANT_URLS = {
  // Главные страницы
  HOME: '/',
  CATALOG: '/products/',
  CART: '/cart/',
  WISHLIST: '/wishlist/',
  ORDERS: '/orders/',
  PROFILE: '/profile/',

  // Услуги
  SERVICES: '/services/',
  SERVICES_DESIGN: '/services/design/',
  SERVICES_ELECTRICAL: '/services/electrical/',
  SERVICES_SOFTWARE: '/services/software/',
  SERVICES_EQUIPMENT: '/services/equipment/',
  SERVICES_SUPPORT: '/services/support/',
  SERVICES_MAINTENANCE: '/services/maintenance/',
  SERVICES_TURNKEY: '/services/', // Под ключ - общая страница услуг

  // Контакты
  CONTACTS: '/contacts/',
  CONTACTS_PHONE: 'tel:+79375246888',
  CONTACTS_EMAIL: 'mailto:info@tech-re.ru',
  CONTACTS_TELEGRAM: 'https://t.me/techresourceru',
  CONTACTS_MAP: 'https://yandex.ru/maps/-/CLtkf21g',

  // ТЗ и КП
  TECH_TASK: '/technical-task/',
  TECH_TASK_FORM: '/technical-task/',
  COMMERCIAL_OFFER: '/technical-task/',

  // Прочее
  BLOG: '/blog/',
  ABOUT: '/about/',
  SUPPORT: '/support/',
  PRIVACY: '/privacy/',
  TURNKEY_PROJECTS: '/turnkey-projects/',

  // Якоря
  REVIEWS_ANCHOR: '/about/#reviews',
  PARTNERS_ANCHOR: '/about/#partners',
  WARRANTY_ANCHOR: '/about/#warranty',

  // Категории товаров (из sitemap)
  CATEGORY_AUTOMATIC_SWITCHES_C: '/products/?category=avtomaticheskie-vyklyuchateli-tip-c',
  CATEGORY_AUTOMATIC_SWITCHES_D: '/products/?category=avtomaticheskie-vyklyuchateli-d-tipa',
  CATEGORY_AUTOMATIC_SWITCHES: '/products/?category=avtomaticheskie-vyklyuchateli',
  CATEGORY_AUTOMATIC_SWITCH_MOTOR: '/products/?category=avtomaticheskij-vyklyuchatel-dlya-zashity-dvigatelya',
  CATEGORY_POWER_SUPPLY: '/products/?category=bloki-pitaniya',
  CATEGORY_DISK_VALVES: '/products/?category=diskovye-zatvory-i-klapany',
  CATEGORY_SCREW_CONVEYOR_PARTS: '/products/?category=zapchasti-k-shnekovym-transportyoram',
  CATEGORY_PRESSURE_RELIEF_VALVE: '/products/?category=klapan-sbrosa-davleniya',
  CATEGORY_TERMINALS: '/products/?category=klemmy',
  CATEGORY_SPRING_TERMINALS: '/products/?category=klemmy-pruzhinnye',
  CATEGORY_CONTACTORS: '/products/?category=kontaktory-magnitnye',
  CATEGORY_CONTACTORS_STARTERS: '/products/?category=kontaktory-puskateli',
  CATEGORY_INTERMEDIATE_SUPPORTS: '/products/?category=opory-promezhutochnye',
  CATEGORY_FREQUENCY_CONVERTERS: '/products/?category=preobrazovatel-chastoty',
  CATEGORY_DISK_VALVE_DRIVES: '/products/?category=privody-diskovyh-zatvorov',
  CATEGORY_REDUCERS: '/products/?category=reduktory',
  CATEGORY_CONVEYOR_REDUCERS: '/products/?category=reduktory-transporterov',
  CATEGORY_SEALS_GLANDS: '/products/?category=uplotneniya-salniki',
  CATEGORY_FILTERS_ASPIRATION: '/products/?category=filtry-aspiracii',
  CATEGORY_SCREW_CONVEYOR: '/products/?category=shnekovyj-transporter',
  CATEGORY_WAM: '/products/?category=wam',

  // Конкретные товары (из sitemap)
  PRODUCT_PREFIX: '/product/', // Префикс для построения ссылок на товары, например: /product/110/
};

// Делаем глобальным
window.ASSISTANT_URLS = ASSISTANT_URLS;