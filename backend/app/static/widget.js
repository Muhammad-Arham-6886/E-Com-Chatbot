/**
 * AI Customer & Commerce Assistant - Embeddable JavaScript Widget
 * Version: 1.0.0
 * Architecture: Zero-dependency Vanilla JS with Shadow DOM isolation
 */
(function () {
  "use strict";

  if (window.__AI_COMMERCE_WIDGET_LOADED__) return;
  window.__AI_COMMERCE_WIDGET_LOADED__ = true;

  var currentScript =
    document.currentScript ||
    (function () {
      var scripts = document.getElementsByTagName("script");
      for (var i = scripts.length - 1; i >= 0; i--) {
        if (scripts[i].getAttribute("data-site-id")) return scripts[i];
      }
      return scripts[scripts.length - 1];
    })();

  if (!currentScript) {
    console.error("[AI Widget] Script tag not found.");
    return;
  }

  var publicSiteId = currentScript.getAttribute("data-site-id");
  var apiUrl = (
    currentScript.getAttribute("data-api-url") ||
    "http://localhost:8000"
  ).replace(/\/+$/, "");

  if (!publicSiteId) {
    console.error("[AI Widget] Missing required 'data-site-id' attribute.");
    return;
  }

  var STORAGE_KEY_SESSION = "ai_widget_token_" + publicSiteId;

  var config = {
    chatbot_name: "Customer Assistant",
    primary_color: "#4f46e5",
    greeting_message: "Hello! How can I help you today?",
    widget_position: "bottom-right",
    enable_whatsapp: false,
    whatsapp_number: null,
  };

  var isOpen = false;
  var sessionToken = null;
  var websiteId = null;
  var isSending = false;

  var hostElement = document.createElement("div");
  hostElement.id = "ai-commerce-widget-root";
  document.body.appendChild(hostElement);

  var shadow = hostElement.attachShadow({ mode: "open" });

  var style = document.createElement("style");
  style.textContent = `
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    
    .widget-container {
      position: fixed;
      z-index: 999999;
      bottom: 24px;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
    }
    .pos-bottom-right { right: 24px; }
    .pos-bottom-left { left: 24px; align-items: flex-start; }

    .launcher-btn {
      width: 58px;
      height: 58px;
      border-radius: 29px;
      border: none;
      background-color: var(--primary-color, #4f46e5);
      color: #ffffff;
      cursor: pointer;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
      outline: none;
    }
    .launcher-btn:hover {
      transform: scale(1.08);
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
    }
    .launcher-btn svg { width: 28px; height: 28px; fill: currentColor; }

    .chat-window {
      width: 380px;
      height: 580px;
      max-height: calc(100vh - 110px);
      max-width: calc(100vw - 48px);
      background-color: #0f172a;
      border: 1px solid #1e293b;
      border-radius: 20px;
      box-shadow: 0 20px 48px rgba(0, 0, 0, 0.45);
      display: flex;
      flex-direction: column;
      margin-bottom: 16px;
      overflow: hidden;
      opacity: 0;
      pointer-events: none;
      transform: translateY(20px) scale(0.96);
      transition: opacity 0.25s ease, transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    .chat-window.open {
      opacity: 1;
      pointer-events: auto;
      transform: translateY(0) scale(1);
    }

    .chat-header {
      background-color: #1e293b;
      padding: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid #334155;
    }
    .header-info { display: flex; align-items: center; gap: 12px; }
    .bot-avatar {
      width: 36px;
      height: 36px;
      border-radius: 12px;
      background-color: var(--primary-color, #4f46e5);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #ffffff;
      font-weight: bold;
      font-size: 14px;
    }
    .header-title { font-size: 14px; font-weight: 700; color: #f8fafc; }
    .header-status { font-size: 11px; color: #10b981; display: flex; align-items: center; gap: 4px; }
    .header-status::before { content: ""; width: 6px; height: 6px; border-radius: 3px; background-color: #10b981; }
    .close-btn {
      background: none;
      border: none;
      color: #94a3b8;
      cursor: pointer;
      padding: 4px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .close-btn:hover { color: #f8fafc; background: #334155; }

    .chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background-color: #0b0f19;
    }
    .chat-messages::-webkit-scrollbar { width: 4px; }
    .chat-messages::-webkit-scrollbar-thumb { background: #334155; border-radius: 2px; }

    .msg-row { display: flex; flex-direction: column; max-width: 85%; }
    .msg-row.user { align-self: flex-end; align-items: flex-end; }
    .msg-row.bot { align-self: flex-start; align-items: flex-start; }

    .msg-bubble {
      padding: 12px 14px;
      font-size: 13px;
      line-height: 1.5;
      border-radius: 16px;
      word-break: break-word;
    }
    .msg-row.user .msg-bubble {
      background-color: var(--primary-color, #4f46e5);
      color: #ffffff;
      border-bottom-right-radius: 4px;
    }
    .msg-row.bot .msg-bubble {
      background-color: #1e293b;
      color: #e2e8f0;
      border: 1px solid #334155;
      border-bottom-left-radius: 4px;
    }

    .sources-list {
      margin-top: 8px;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      font-size: 10px;
    }
    .source-tag {
      background: #0f172a;
      border: 1px solid #334155;
      color: #818cf8;
      padding: 3px 8px;
      border-radius: 6px;
      text-decoration: none;
      max-width: 180px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .source-tag:hover { text-decoration: underline; color: #a5b4fc; }

    .product-cards {
      margin-top: 8px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      width: 100%;
    }
    .product-card {
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 10px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .product-img {
      width: 48px;
      height: 48px;
      border-radius: 8px;
      object-fit: cover;
      background: #1e293b;
      flex-shrink: 0;
    }
    .product-info { flex: 1; min-width: 0; }
    .product-title { font-size: 12px; font-weight: 600; color: #f8fafc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .product-price { font-size: 11px; font-weight: 700; color: #10b981; margin-top: 2px; }
    .product-btn {
      background: var(--primary-color, #4f46e5);
      color: #ffffff;
      padding: 6px 10px;
      border-radius: 8px;
      font-size: 11px;
      font-weight: 600;
      text-decoration: none;
      flex-shrink: 0;
      transition: opacity 0.2s;
    }
    .product-btn:hover { opacity: 0.9; }

    .whatsapp-action-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background-color: #059669;
      color: #ffffff;
      padding: 8px 12px;
      border-radius: 10px;
      font-size: 12px;
      font-weight: 600;
      text-decoration: none;
      margin-top: 8px;
      box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
      transition: background 0.2s;
    }
    .whatsapp-action-btn:hover { background-color: #10b981; }

    .typing-indicator {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 10px 14px;
      background: #1e293b;
      border-radius: 14px;
      border-bottom-left-radius: 4px;
      width: fit-content;
    }
    .dot {
      width: 6px;
      height: 6px;
      background: #94a3b8;
      border-radius: 50%;
      animation: wave 1.2s infinite ease-in-out;
    }
    .dot:nth-child(2) { animation-delay: 0.2s; }
    .dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes wave { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-5px); } }

    .chat-footer {
      padding: 12px;
      background: #1e293b;
      border-top: 1px solid #334155;
    }
    .input-form { display: flex; gap: 8px; align-items: center; }
    .chat-input {
      flex: 1;
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 10px 14px;
      font-size: 13px;
      color: #f8fafc;
      outline: none;
      transition: border-color 0.2s;
    }
    .chat-input:focus { border-color: var(--primary-color, #4f46e5); }
    .chat-input::placeholder { color: #64748b; }
    .send-btn {
      width: 38px;
      height: 38px;
      border-radius: 12px;
      border: none;
      background: var(--primary-color, #4f46e5);
      color: #ffffff;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: opacity 0.2s;
      flex-shrink: 0;
    }
    .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
    .branding {
      text-align: center;
      font-size: 10px;
      color: #64748b;
      margin-top: 6px;
    }
  `;
  shadow.appendChild(style);

  var container = document.createElement("div");
  container.className = "widget-container pos-bottom-right";
  container.innerHTML = `
    <div class="chat-window" id="chatWindow">
      <div class="chat-header">
        <div class="header-info">
          <div class="bot-avatar" id="botAvatar">AI</div>
          <div>
            <div class="header-title" id="botName">Customer Assistant</div>
            <div class="header-status">Online</div>
          </div>
        </div>
        <div class="header-actions" style="display: flex; align-items: center; gap: 8px;">
          <a class="header-wa-btn" id="headerWaBtn" style="display: none; color: #22c55e; background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 8px; padding: 4px 8px; font-size: 11px; font-weight: 600; text-decoration: none; align-items: center; gap: 4px;" target="_blank" rel="noreferrer" title="Chat on WhatsApp">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M12.04 2c-5.46 0-9.91 4.45-9.91 9.91 0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38c1.45.79 3.08 1.21 4.74 1.21 5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.816 9.816 0 0 0 12.04 2z"/></svg>
            <span>WhatsApp</span>
          </a>
          <button class="close-btn" id="closeBtn" aria-label="Close chat">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"></path></svg>
          </button>
        </div>
      </div>

      <div class="chat-messages" id="messagesArea"></div>

      <div class="chat-footer">
        <form class="input-form" id="inputForm">
          <input type="text" class="chat-input" id="messageInput" placeholder="Type a message..." autocomplete="off" />
          <button type="submit" class="send-btn" id="sendBtn" aria-label="Send">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
          </button>
        </form>
        <div class="branding">Powered by AI Customer & Commerce Assistant</div>
      </div>
    </div>

    <button class="launcher-btn" id="launcherBtn" aria-label="Open chat">
      <svg id="launcherIconOpen" viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"></path></svg>
      <svg id="launcherIconClose" viewBox="0 0 24 24" style="display:none;"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"></path></svg>
    </button>
  `;
  shadow.appendChild(container);

  var chatWindow = shadow.getElementById("chatWindow");
  var launcherBtn = shadow.getElementById("launcherBtn");
  var launcherIconOpen = shadow.getElementById("launcherIconOpen");
  var launcherIconClose = shadow.getElementById("launcherIconClose");
  var closeBtn = shadow.getElementById("closeBtn");
  var messagesArea = shadow.getElementById("messagesArea");
  var inputForm = shadow.getElementById("inputForm");
  var messageInput = shadow.getElementById("messageInput");
  var sendBtn = shadow.getElementById("sendBtn");
  var botNameEl = shadow.getElementById("botName");

  var CURRENCY_SYMBOLS = {
    USD: "$", GBP: "£", EUR: "€", AUD: "A$", CAD: "C$",
    INR: "₹", PKR: "₨", JPY: "¥", CNY: "¥", AED: "د.إ"
  };
  function fmtPrice(p) {
    var num = Number(p.price);
    if (isNaN(num)) num = 0;
    var sym = CURRENCY_SYMBOLS[p.currency] || (p.currency ? p.currency + " " : "£");
    return sym + num.toFixed(2);
  }

  function formatMarkdown(text) {
    if (!text) return "";
    var escaped = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    escaped = escaped.replace(/\n/g, "<br/>");
    return escaped;
  }

  function renderMessage(msg) {
    var row = document.createElement("div");
    row.className = "msg-row " + (msg.sender === "USER" ? "user" : "bot");

    var bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.innerHTML = formatMarkdown(msg.content);
    row.appendChild(bubble);

    if (msg.suggested_actions) {
      var prodCards = msg.suggested_actions.filter(function (a) {
        return a.type === "product_card" && a.payload;
      });
      if (prodCards.length > 0) {
        var cardsContainer = document.createElement("div");
        cardsContainer.className = "product-cards";
        prodCards.forEach(function (act) {
          var p = act.payload;
          var card = document.createElement("div");
          card.className = "product-card";
          card.innerHTML = `
            ${p.image_url ? '<img src="' + p.image_url + '" class="product-img" alt="' + p.name + '" />' : ''}
            <div class="product-info">
              <div class="product-title">${p.name}</div>
              <div class="product-price">${fmtPrice(p)}</div>
            </div>
            <a href="${act.value}" target="_blank" rel="noreferrer" class="product-btn">View</a>
          `;
          cardsContainer.appendChild(card);
        });
        row.appendChild(cardsContainer);
      }

      var waActions = msg.suggested_actions.filter(function (a) {
        return a.type === "whatsapp_handoff";
      });
      if (waActions.length > 0) {
        waActions.forEach(function (act) {
          var waBtn = document.createElement("a");
          waBtn.className = "whatsapp-action-btn";
          waBtn.href = act.value;
          waBtn.target = "_blank";
          waBtn.rel = "noreferrer";
          waBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12.04 2c-5.46 0-9.91 4.45-9.91 9.91 0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38c1.45.79 3.08 1.21 4.74 1.21 5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.816 9.816 0 0012.04 2z"/></svg>
            <span>${act.label || "Chat on WhatsApp"}</span>
          `;
          row.appendChild(waBtn);
        });
      }
    }

    if (msg.sources && msg.sources.length > 0) {
      var sourcesContainer = document.createElement("div");
      sourcesContainer.className = "sources-list";
      msg.sources.forEach(function (src) {
        var a = document.createElement("a");
        a.className = "source-tag";
        a.href = src.url;
        a.target = "_blank";
        a.rel = "noreferrer";
        a.textContent = "📄 " + src.title;
        sourcesContainer.appendChild(a);
      });
      row.appendChild(sourcesContainer);
    }

    messagesArea.appendChild(row);
    messagesArea.scrollTop = messagesArea.scrollHeight;
  }

  var typingEl = null;
  function showTyping() {
    if (typingEl) return;
    typingEl = document.createElement("div");
    typingEl.className = "msg-row bot";
    typingEl.innerHTML = '<div class="typing-indicator"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>';
    messagesArea.appendChild(typingEl);
    messagesArea.scrollTop = messagesArea.scrollHeight;
  }

  function hideTyping() {
    if (typingEl && typingEl.parentNode) {
      typingEl.parentNode.removeChild(typingEl);
      typingEl = null;
    }
  }

  function toggleChat(open) {
    isOpen = typeof open === "boolean" ? open : !isOpen;
    if (isOpen) {
      chatWindow.classList.add("open");
      launcherIconOpen.style.display = "none";
      launcherIconClose.style.display = "block";
      messageInput.focus();
    } else {
      chatWindow.classList.remove("open");
      launcherIconOpen.style.display = "block";
      launcherIconClose.style.display = "none";
    }
  }

  launcherBtn.addEventListener("click", function () { toggleChat(); });
  closeBtn.addEventListener("click", function () { toggleChat(false); });

  function initSession(callback) {
    sessionToken = localStorage.getItem(STORAGE_KEY_SESSION);
    if (sessionToken) {
      if (callback) callback();
      return;
    }

    fetch(apiUrl + "/api/v1/chat/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        website_id: websiteId,
        channel: "WEB_WIDGET",
      }),
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data && data.session_token) {
          sessionToken = data.session_token;
          localStorage.setItem(STORAGE_KEY_SESSION, sessionToken);
        }
        if (callback) callback();
      })
      .catch(function (err) {
        console.error("[AI Widget] Session init failed:", err);
      });
  }

  inputForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = messageInput.value.trim();
    if (!text || isSending) return;

    messageInput.value = "";
    isSending = true;
    sendBtn.disabled = true;

    var userMsg = { sender: "USER", content: text };
    renderMessage(userMsg);
    showTyping();

    function doSend() {
      fetch(apiUrl + "/api/v1/chat/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_token: sessionToken,
          content: text,
        }),
      })
        .then(function (res) {
          if (!res.ok) throw new Error("Server responded with " + res.status);
          return res.json();
        })
        .then(function (data) {
          hideTyping();
          renderMessage(data);
        })
        .catch(function (err) {
          hideTyping();
          renderMessage({
            sender: "BOT",
            content: "I'm having trouble connecting to the store right now. Please try again in a moment.",
          });
        })
        .finally(function () {
          isSending = false;
          sendBtn.disabled = false;
          messageInput.focus();
        });
    }

    if (!sessionToken) {
      initSession(doSend);
    } else {
      doSend();
    }
  });

  fetch(apiUrl + "/api/v1/websites/public/" + publicSiteId + "/config")
    .then(function (res) {
      if (!res.ok) throw new Error("Failed to load website widget config");
      return res.json();
    })
    .then(function (data) {
      websiteId = data.website_id;
      config.chatbot_name = data.chatbot_name || config.chatbot_name;
      config.primary_color = data.primary_color || config.primary_color;
      config.greeting_message = data.welcome_message || config.greeting_message;
      config.widget_position = data.launcher_position || config.widget_position;
      config.enable_whatsapp = data.enable_whatsapp !== undefined ? data.enable_whatsapp : config.enable_whatsapp;
      config.whatsapp_number = data.whatsapp_number || config.whatsapp_number;

      hostElement.style.setProperty("--primary-color", config.primary_color);
      botNameEl.textContent = config.chatbot_name;

      if (config.widget_position === "bottom-left") {
        container.className = "widget-container pos-bottom-left";
      }

      if (data.enable_whatsapp && data.whatsapp_number && data.whatsapp_handoff_trigger === "ALWAYS_VISIBLE") {
        var headerWaBtn = shadow.getElementById("headerWaBtn");
        if (headerWaBtn) {
          var cleanPhone = (data.whatsapp_number || "").replace(/\D/g, "");
          var waText = data.whatsapp_custom_message || "Hello! I am browsing " + (data.website_name || "your store") + " and need assistance.";
          headerWaBtn.href = "https://wa.me/" + cleanPhone + "?text=" + encodeURIComponent(waText);
          headerWaBtn.style.display = "inline-flex";
        }
      }

      renderMessage({
        sender: "BOT",
        content: config.greeting_message,
      });

      initSession();
    })
    .catch(function (err) {
      console.error("[AI Widget] Initialization error:", err);
    });
})();
