  // static/js/assistant/smart_assistant.js

  class SmartAssistant {
    constructor() {
      this.isOpen = false;
      this.messages = [];
      this.context = {
        currentPage: window.location.pathname,
        visitedPages: [window.location.pathname],
        productViews: [],
        cartItems: 0,
      };
      this.apiUrl = '/api/assistant/';
      this.knowledgeBase = {};
      this.urls = {};
      this.loadData();
      this.init();
    }

    loadData() {
      // Загружаем данные из глобальных объектов
      const dataSources = [
        'ASSISTANT_URLS',
        'ASSISTANT_GREETINGS',
        'ASSISTANT_SERVICES',
        'ASSISTANT_AUTOMATION',
        'ASSISTANT_PRICES',
        'ASSISTANT_PRODUCTS',
        'ASSISTANT_CONTACTS',
        'ASSISTANT_DELIVERY',
        'ASSISTANT_WARRANTY',
        'ASSISTANT_PAYMENT',
        'ASSISTANT_TECH_TASK',
        'ASSISTANT_PROJECTS',
        'ASSISTANT_PARTNERS',
        'ASSISTANT_BLOG',
        'ASSISTANT_REVIEWS',
        'ASSISTANT_SUPPORT',
        'ASSISTANT_TRAINING',
        'ASSISTANT_SECURITY',
        'ASSISTANT_INDUSTRIES',
        'ASSISTANT_EQUIPMENT'
      ];

      for (const name of dataSources) {
        if (window[name]) {
          if (name === 'ASSISTANT_URLS') {
            this.urls = window[name];
          } else {
            const key = name.replace('ASSISTANT_', '').toLowerCase();
            this.knowledgeBase[key] = window[name];
          }
        }
      }
    }

    async init() {
      await this.getCartCount();
      this.createChatWidget();
      this.trackBehavior();
      this.initHotkeys();
    }

    async getCartCount() {
      try {
        const response = await fetch('/cart/api/count/');
        const data = await response.json();
        this.context.cartItems = data.count || 0;
      } catch (e) {
        const badge = document.querySelector('.cart-badge');
        if (badge) this.context.cartItems = parseInt(badge.textContent) || 0;
      }
    }

    trackBehavior() {
      const observer = new MutationObserver(() => {
        document.querySelectorAll('.product-card, [data-product-id]').forEach(card => {
          if (!card.dataset.observed) {
            card.dataset.observed = 'true';
            const link = card.querySelector('a');
            if (link) {
              link.addEventListener('click', () => {
                const productId = link.href?.split('/').pop();
                if (productId && !this.context.productViews.includes(productId)) {
                  this.context.productViews.push(productId);
                }
              });
            }
          }
        });
      });
      observer.observe(document.body, { childList: true, subtree: true });

      let lastPath = window.location.pathname;
      setInterval(() => {
        const newPath = window.location.pathname;
        if (newPath !== lastPath) {
          this.context.visitedPages.push(newPath);
          lastPath = newPath;
        }
      }, 1000);
    }

    createChatWidget() {
      const styles = document.createElement('style');
      styles.id = 'assistant-styles';
      styles.textContent = `
        .assistant-chat-btn {
          position: fixed;
          bottom: 12px;
          right: 26px;
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: rgba(44, 62, 80, 0.95);
          border: none;
          box-shadow: 0 4px 20px rgba(18, 18, 19, 0.5);
          cursor: pointer;
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
          color: white;
          font-size: 18px;
        }
        .assistant-chat-btn:hover { transform: scale(1.05); }
        .assistant-chat-btn .badge {
          position: absolute;
          top: -4px;
          right: -4px;
          width: 18px;
          height: 18px;
          background: #48bb78;
          border-radius: 50%;
          font-size: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: bold;
        }
        .assistant-chat-window {
          position: fixed;
          bottom: 70px;
          right: 16px;
          width: 400px;
          max-height: 560px;
          background: white;
          border-radius: 12px;
          box-shadow: 0 10px 40px rgba(0,0,0,0.2);
          z-index: 9998;
          display: none;
          flex-direction: column;
          overflow: hidden;
          border: 1px solid rgba(0,0,0,0.08);
        }
        .assistant-chat-window.open { display: flex; }
        .chat-header {
          padding: 14px 18px;
          background: rgba(44, 62, 80, 0.95);
          color: white;
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-shrink: 0;
        }
        .chat-header-left { display: flex; align-items: center; gap: 10px; }
        .chat-header-left .avatar {
          width: 32px;
          height: 32px;
          background: rgba(255,255,255,0.15);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 16px;
        }
        .chat-header-left .title { font-weight: 600; font-size: 14px; }
        .chat-header-left .status { font-size: 11px; opacity: 0.8; }
        .chat-close {
          background: none;
          border: none;
          color: white;
          cursor: pointer;
          font-size: 18px;
          opacity: 0.7;
          padding: 4px 8px;
        }
        .chat-close:hover { opacity: 1; }
        .chat-messages {
          flex: 1;
          padding: 16px;
          overflow-y: auto;
          background: #f8f9fa;
          max-height: 360px;
          min-height: 200px;
        }
        .chat-messages::-webkit-scrollbar { width: 4px; }
        .chat-messages::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }
        .message {
          margin-bottom: 10px;
          max-width: 88%;
          animation: messageIn 0.3s ease;
        }
        @keyframes messageIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .message.bot { align-self: flex-start; }
        .message.user { align-self: flex-end; margin-left: auto; }
        .message .bubble {
          padding: 8px 14px;
          border-radius: 12px;
          font-size: 14px;
          line-height: 1.5;
          word-wrap: break-word;
        }
        .message.bot .bubble {
          background: white;
          color: #1a1a2e;
          border-bottom-left-radius: 4px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }
        .message.user .bubble {
          background: rgba(44, 62, 80, 0.95);
          color: white;
          border-bottom-right-radius: 4px;
        }
        .message .time {
          font-size: 10px;
          color: #999;
          margin-top: 3px;
          padding: 0 4px;
        }
        .message.user .time { text-align: right; }
        .quick-actions {
          padding: 8px 12px;
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
          background: white;
          border-top: 1px solid #f0f0f0;
          flex-shrink: 0;
        }
        .quick-actions button {
          padding: 5px 12px;
          border: 1px solid #e5e5e5;
          border-radius: 16px;
          background: white;
          color: #555;
          font-size: 12px;
          cursor: pointer;
          transition: all 0.2s;
        }
        .quick-actions button:hover {
          border-color: #2c3e50;
          color: #2c3e50;
          background: #f5f5f5;
        }
        .chat-input-area {
          padding: 10px 14px 14px;
          background: white;
          border-top: 1px solid #f0f0f0;
          display: flex;
          gap: 8px;
          flex-shrink: 0;
          align-items: flex-end;
        }
        .chat-input-area textarea {
          flex: 1;
          border: 1px solid #e5e5e5;
          border-radius: 10px;
          padding: 8px 12px;
          font-size: 14px;
          resize: none;
          outline: none;
          font-family: inherit;
          min-height: 36px;
          max-height: 72px;
          line-height: 1.4;
        }
        .chat-input-area textarea:focus { border-color: #2c3e50; }
        .chat-input-area .send-btn {
          padding: 8px 14px;
          background: rgba(44, 62, 80, 0.95);
          color: white;
          border: none;
          border-radius: 10px;
          cursor: pointer;
          font-size: 16px;
          transition: all 0.2s;
          height: 38px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .chat-input-area .send-btn:hover { background: #2c3e50; }
        .chat-input-area .send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .typing-indicator {
          display: none;
          padding: 8px 14px;
          background: white;
          border-radius: 12px;
          border-bottom-left-radius: 4px;
          margin-bottom: 10px;
          width: fit-content;
          box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }
        .typing-indicator.active { display: block; }
        .typing-indicator span {
          display: inline-block;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #999;
          margin: 0 2px;
          animation: typing 1.4s infinite;
        }
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typing {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
          30% { transform: translateY(-8px); opacity: 1; }
        }
        .message .bubble a { color: #2c3e50; text-decoration: underline; }
        .message.user .bubble a { color: #fff; }
        @media (max-width: 480px) {
          .assistant-chat-window {
            width: calc(100vw - 24px);
            right: 12px;
            bottom: 70px;
            max-height: 440px;
          }
          .assistant-chat-btn {
            width: 44px;
            height: 44px;
            bottom: 12px;
            right: 12px;
            font-size: 16px;
          }
        }
      `;
      document.head.appendChild(styles);

      const btn = document.createElement('button');
      btn.className = 'assistant-chat-btn';
      btn.innerHTML = `<i class="fas fa-robot"></i><span class="badge">AI</span>`;
      btn.title = 'ИИ-помощник (Ctrl+Alt+H)';
      btn.addEventListener('click', () => this.toggleChat());
      document.body.appendChild(btn);

      const windowEl = document.createElement('div');
      windowEl.className = 'assistant-chat-window';
      windowEl.innerHTML = `
        <div class="chat-header">
          <div class="chat-header-left">
            <div class="avatar">🤖</div>
            <div>
              <div class="title">ИИ-помощник</div>
              <div class="status">● Онлайн</div>
            </div>
          </div>
          <button class="chat-close">✕</button>
        </div>
        <div class="chat-messages" id="chatMessages">
          <div class="typing-indicator" id="typingIndicator">
            <span></span><span></span><span></span>
          </div>
        </div>
        <div class="quick-actions">
          <button data-question="Услуги">Услуги</button>
          <button data-question="Монтаж">Монтаж</button>
          <button data-question="Заказ">Заказ</button>
          <button data-question="Контакты">Контакты</button>
          <button data-question="Цена">Цена</button>
        </div>
        <div class="chat-input-area">
          <textarea placeholder="Спросите что-нибудь..." id="chatInput" rows="1"></textarea>
          <button class="send-btn" id="sendBtn">
            <i class="fas fa-arrow-up"></i>
          </button>
        </div>
      `;
      document.body.appendChild(windowEl);

      windowEl.querySelector('.chat-close').addEventListener('click', () => this.toggleChat(false));

      const input = windowEl.querySelector('#chatInput');
      const sendBtn = windowEl.querySelector('#sendBtn');

      const sendMessage = () => {
        const text = input.value.trim();
        if (text) {
          this.sendUserMessage(text);
          input.value = '';
          input.style.height = '36px';
        }
      };

      sendBtn.addEventListener('click', sendMessage);
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendMessage();
        }
      });
      input.addEventListener('input', () => {
        input.style.height = '36px';
        input.style.height = Math.min(input.scrollHeight, 72) + 'px';
      });

      windowEl.querySelectorAll('.quick-actions button').forEach(btn => {
        btn.addEventListener('click', () => {
          this.sendUserMessage(btn.dataset.question);
        });
      });

      setTimeout(() => {
        const greeting = this.getGreeting();
        this.addMessage('bot', greeting);
      }, 500);

      this.chatWindow = windowEl;
      this.chatMessages = windowEl.querySelector('#chatMessages');
      this.typingIndicator = windowEl.querySelector('#typingIndicator');
      this.input = input;
      this.sendBtn = sendBtn;
    }

    toggleChat(open) {
      this.isOpen = open !== undefined ? open : !this.isOpen;
      this.chatWindow.classList.toggle('open', this.isOpen);
      if (this.isOpen) {
        this.input.focus();
        this.scrollToBottom();
      }
    }

    getGreeting() {
      const hour = new Date().getHours();
      let time = hour < 12 ? 'Доброе утро' : hour < 18 ? 'Добрый день' : 'Добрый вечер';
      const page = window.location.pathname;
      let context = '';
      if (page.includes('/product/')) context = 'Хотите узнать о товаре?';
      else if (page === '/cart/') context = 'Готовы оформить заказ?';
      else if (page.includes('/services/')) context = 'Расскажу об услугах!';
      else context = 'Чем могу помочь?';
      return `${time}! Я помощник Техресурс. ${context}`;
    }

    addMessage(type, text, time) {
      this.typingIndicator.classList.remove('active');
      const msgDiv = document.createElement('div');
      msgDiv.className = `message ${type}`;
      const timeStr = time || new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
      msgDiv.innerHTML = `
        <div class="bubble">${this.formatMessage(text)}</div>
        <div class="time">${timeStr}</div>
      `;
      this.chatMessages.insertBefore(msgDiv, this.typingIndicator);
      this.scrollToBottom();
      this.messages.push({ type, text, time: timeStr });
    }

    formatMessage(text) {
      // Сначала заменяем плейсхолдеры на реальные URL (если еще не сделано)
      if (this.urls && Object.keys(this.urls).length > 0) {
        for (const [key, value] of Object.entries(this.urls)) {
          const placeholder = `{{URL_${key.toUpperCase()}}}`;
          if (text.includes(placeholder)) {
            text = text.replace(new RegExp(placeholder, 'g'), value);
          }
        }
      }
      
      // Превращаем /пути/ в ссылки (внутренние ссылки сайта)
      text = text.replace(/(\/[a-zA-Z0-9_\-\/]+)/g, function(match) {
        // Проверяем, что это не часть слова и не email/телефон
        return `<a href="${match}" target="_blank">${match}</a>`;
      });
      
      // Внешние ссылки
      text = text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
      
      // Email
      text = text.replace(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g, '<a href="mailto:$1">$1</a>');
      
      // Телефоны
      text = text.replace(/(\+?[0-9][0-9\s\-\(\)]{7,}[0-9])/g, '<a href="tel:$1">$1</a>');
      
      // Переносы строк
      text = text.replace(/\n/g, '<br>');
      
      return text;
    }

    async sendUserMessage(text) {
      if (this.isLoading) return;
      this.addMessage('user', text);
      this.isLoading = true;
      this.sendBtn.disabled = true;
      this.typingIndicator.classList.add('active');
      this.scrollToBottom();

      try {
        const response = await this.getAIResponse(text);
        const formattedResponse = this.replaceUrls(response);
        this.typingIndicator.classList.remove('active');
        await this.delay(200 + Math.random() * 300);
        this.addMessage('bot', formattedResponse);

        if (this.messages.length <= 4) {
          const quick = this.getQuickReplies(text);
          if (quick) {
            await this.delay(500);
            this.addMessage('bot', this.replaceUrls(quick));
          }
        }
      } catch (error) {
        this.typingIndicator.classList.remove('active');
        this.addMessage('bot', 'Извините, произошла ошибка. Попробуйте переформулировать вопрос или свяжитесь с нами по телефону.');
      }

      this.isLoading = false;
      this.sendBtn.disabled = false;
      this.input.focus();
    }

    async getAIResponse(text) {
      const localResponse = this.getLocalResponse(text);
      if (localResponse) return localResponse;

      try {
        const response = await fetch(this.apiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
          },
          body: JSON.stringify({
            message: text,
            context: {
              page: this.context.currentPage,
              visitedPages: this.context.visitedPages.slice(-5),
              productViews: this.context.productViews,
              cartItems: this.context.cartItems,
            }
          })
        });

        if (response.ok) {
          const data = await response.json();
          if (data.response) return data.response;
        }
      } catch (e) {}

      return this.getFallbackResponse(text);
    }

    getLocalResponse(text) {
      const lower = text.toLowerCase().trim();

      // Проверяем приветствия
      if (this.knowledgeBase.greetings && this.knowledgeBase.greetings.keywords) {
        for (const keyword of this.knowledgeBase.greetings.keywords) {
          if (new RegExp(keyword, 'i').test(lower)) {
            return this.replaceUrls(this.knowledgeBase.greetings.main);
          }
        }
      }

      // Проверяем все разделы
      const sections = [
        'automation', 'services', 'prices', 'products', 'contacts',
        'delivery', 'warranty', 'payment', 'tech_task', 'projects',
        'partners', 'blog', 'reviews', 'support', 'training', 'security',
        'industries', 'equipment'
      ];

      for (const sectionName of sections) {
        const section = this.knowledgeBase[sectionName];
        if (!section || !section.keywords) continue;

        for (const keyword of section.keywords) {
          if (new RegExp(keyword, 'i').test(lower)) {
            // Проверяем под-вопросы
            if (section.sub_answers) {
              for (const [subKey, answer] of Object.entries(section.sub_answers)) {
                if (new RegExp(subKey, 'i').test(lower)) {
                  return this.replaceUrls(answer);
                }
              }
            }
            return this.replaceUrls(section.main);
          }
        }
      }

      // Проверяем ссылки
      for (const sectionName of sections) {
        const section = this.knowledgeBase[sectionName];
        if (!section || !section.links) continue;
        for (const [linkKey, linkUrl] of Object.entries(section.links)) {
          if (new RegExp(linkKey, 'i').test(lower)) {
            const resolvedUrl = this.replaceUrls(linkUrl);
            return `Вот что вам нужно:\n\n${resolvedUrl}`;
          }
        }
      }

      // Smart анализ
      const smartResult = this.smartAnalyze(lower);
      if (smartResult) return smartResult;

      return null;
    }

    smartAnalyze(text) {
      const topics = {
        'автоматизация|асутп|управление|контроль|процесс': 'automation',
        'цена|стоимость|сколько|прайс|бюджет': 'prices',
        'заказ|купить|корзина|оформить': 'products',
        'контакт|телефон|адрес|связаться': 'contacts',
        'доставка|отправка|транспорт|перевозка': 'delivery',
        'гарантия|ремонт|сервис|поломка': 'warranty',
        'оплата|счет|реквизиты|ндс': 'payment',
        'техзадание|тз|кп|проект': 'tech_task',
      };

      for (const [keys, sectionName] of Object.entries(topics)) {
        if (new RegExp(keys, 'i').test(text)) {
          const section = this.knowledgeBase[sectionName];
          if (section && section.main) {
            return this.replaceUrls(section.main);
          }
        }
      }

      if (/(хочу|нужно|помогите|подскажите|посоветуйте|хотел бы|хотела бы|нужна помощь)/i.test(text)) {
        return this.replaceUrls(`Давайте разберемся!

  Я вижу, что вам нужна помощь. Расскажите подробнее:
  - Что вы хотите автоматизировать?
  - Какое оборудование интересует?
  - Какой бюджет?

  Я подберу оптимальное решение!

  Или заполните техзадание: /technical-task/`);
      }

      return null;
    }

    replaceUrls(text) {
      if (!text || !this.urls) return text;
      for (const [key, value] of Object.entries(this.urls)) {
        const placeholder = `{{URL_${key.toUpperCase()}}}`;
        if (text.includes(placeholder)) {
          text = text.replace(new RegExp(placeholder, 'g'), value);
        }
      }
      return text;
    }

    getFallbackResponse(text) {
      return `Спасибо за вопрос!

  Я могу помочь с темами:

  Услуги:
  - Проектирование систем автоматизации
  - Электромонтажные работы
  - Разработка ПО и SCADA
  - Поставка оборудования
  - Техническая поддержка

  Заказ и покупка:
  - Как заказать оборудование
  - Способы оплаты
  - Доставка по России
  - Гарантия и сервис

  Контакты:
  - Телефон: +7 (937) 524-68-88
  - Email: info@tech-re.ru
  - Telegram: @techresourceru

  Для точного расчета:
  Заполните техзадание: /technical-task/

  Что именно вас интересует? Напишите подробнее.`;
    }

    getQuickReplies(text) {
      const lower = text.toLowerCase();

      if (lower.includes('услуг') || lower.includes('делает') || lower.includes('занимает')) {
        return 'Напишите: "Проектирование", "Монтаж", "Разработка ПО", "Поставка" или "Сервис" для подробностей.';
      }

      if (lower.includes('монтаж') || lower.includes('установк')) {
        return 'Для расчета стоимости монтажа заполните техзадание с указанием объема работ.';
      }

      if (lower.includes('заказ') || lower.includes('купить')) {
        return 'Перейдите в каталог, добавьте товары в корзину и оформите заказ. Нужна помощь с выбором?';
      }

      if (lower.includes('цена') || lower.includes('стоимость') || lower.includes('сколько')) {
        return 'Укажите модель оборудования или опишите задачу для точного расчета.';
      }

      if (lower.includes('контакт') || lower.includes('связаться') || lower.includes('телефон')) {
        return 'Телефон: +7 (937) 524-68-88, Email: info@tech-re.ru, Telegram: @techresourceru';
      }

      return null;
    }

    delay(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    }

    scrollToBottom() {
      setTimeout(() => {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
      }, 50);
    }

    initHotkeys() {
      document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.altKey && e.key === 'h') {
          e.preventDefault();
          this.toggleChat();
        }
      });
    }
  }

  // Инициализация
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new SmartAssistant());
  } else {
    new SmartAssistant();
  }