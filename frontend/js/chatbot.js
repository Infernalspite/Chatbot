// chatbot.js - Bookkeeper's Drawer (Floating Chatbot Widget)

(function () {
    // Injects stylesheet for chatbot
    const style = document.createElement('style');
    style.innerHTML = `
        #chatbot-drawer {
            position: fixed;
            bottom: 80px;
            right: 24px;
            width: 380px;
            height: 500px;
            background: #fdf9f2;
            border: 2px solid #1c1b19;
            box-shadow: 6px 6px 0px 0px #1c1b19;
            z-index: 1000;
            display: none;
            flex-direction: column;
            background-image: url("https://www.transparenttextures.com/patterns/natural-paper.png");
        }
        @media (max-width: 480px) {
            #chatbot-drawer {
                width: 100%;
                height: 100%;
                bottom: 0;
                right: 0;
                border: none;
                box-shadow: none;
            }
        }
        #chatbot-messages {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .chat-bubble {
            max-width: 85%;
            padding: 10px 14px;
            border: 1px solid #1c1b19;
            box-shadow: 2px 2px 0px 0px #1c1b19;
            font-size: 14px;
            line-height: 1.5;
        }
        .chat-bubble.user {
            align-self: flex-end;
            background: #ffdbd1; /* Primary Dim */
        }
        .chat-bubble.assistant {
            align-self: flex-start;
            background: #ffffff; /* Paper */
        }
        #chatbot-input-area {
            border-top: 2px solid #1c1b19;
            padding: 12px;
            background: #f7f3ec;
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .suggestion-chip {
            font-size: 11px;
            border: 1px solid #1c1b19;
            padding: 4px 8px;
            background: #ffffff;
            cursor: pointer;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .suggestion-chip:hover {
            background: #c1502e;
            color: #ffffff;
        }
    `;
    document.head.appendChild(style);

    // Get API_URL from environment or fallback
    const API_URL = ""; // Relative url since it's hosted on same server!

    // Session-based chat history
    let chatHistory = JSON.parse(sessionStorage.getItem('chatbot_history') || '[]');

    // Inject drawer HTML
    const drawer = document.createElement('div');
    drawer.id = 'chatbot-drawer';
    drawer.innerHTML = `
        <div class="flex justify-between items-center bg-[#1c1b19] text-white p-3">
            <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-primary text-xl">menu_book</span>
                <span class="font-bold font-serif">The Bookkeeper</span>
            </div>
            <button onclick="toggleChatbot()" class="text-white hover:text-primary transition-colors">
                <span class="material-symbols-outlined">close</span>
            </button>
        </div>
        <div class="bg-[#ceeace] text-[#09200f] px-3 py-1 text-xs font-semibold border-b border-[#1c1b19] flex gap-2 overflow-x-auto whitespace-nowrap py-2" id="chatbot-suggestions">
            <button class="suggestion-chip" onclick="sendSuggestion('What is in my cart?')">🛒 Cart Summary</button>
            <button class="suggestion-chip" onclick="sendSuggestion('Where is my delivery?')">🚚 Tracking status</button>
            <button class="suggestion-chip" onclick="sendSuggestion('Which products are low on stock?')">🚨 Stock warnings</button>
        </div>
        <div id="chatbot-messages"></div>
        <div id="chatbot-input-area">
            <input type="text" id="chatbot-input" placeholder="Inquire about items or orders..." class="notepad-line flex-1 text-sm bg-transparent" />
            <button onclick="sendChatMessage()" class="bg-[#c1502e] text-white px-4 py-2 border-2 border-[#1c1b19] hard-shadow hover:translate-y-[1px] hover:shadow-[2px_2px_0px_0px_rgba(28,27,25,1)] transition-all font-bold text-xs">ASK</button>
        </div>
    `;
    document.body.appendChild(drawer);

    // Inject floating button HTML
    const floatBtn = document.createElement('button');
    floatBtn.id = 'chatbot-float-btn';
    floatBtn.className = 'fixed bottom-20 md:bottom-8 right-6 md:right-8 w-14 h-14 bg-[#c1502e] text-white border-2 border-[#1c1b19] shadow-[4px_4px_0px_0px_rgba(28,27,25,1)] transition-all z-[999] flex items-center justify-center hover:rotate-3 active:translate-x-1 active:translate-y-1 active:shadow-none';
    floatBtn.style.transform = 'rotate(-2deg)';
    floatBtn.innerHTML = `<span class="material-symbols-outlined text-3xl">forum</span>`;
    floatBtn.onclick = toggleChatbot;
    document.body.appendChild(floatBtn);

    const chatbotMessages = document.getElementById('chatbot-messages');
    const chatbotInput = document.getElementById('chatbot-input');

    // Toggle drawer visibility
    window.toggleChatbot = function () {
        const isVisible = drawer.style.display === 'flex';
        drawer.style.display = isVisible ? 'none' : 'flex';
        if (!isVisible) {
            renderHistory();
            chatbotInput.focus();
        }
    };

    // Render historical messages
    function renderHistory() {
        chatbotMessages.innerHTML = '';
        if (chatHistory.length === 0) {
            appendMessage('assistant', "Greetings, resident. I am the local Bookkeeper. Ask me about local listings, cart totals, or delivery updates.");
        } else {
            chatHistory.forEach(msg => {
                appendMessage(msg.role, msg.content, false);
            });
        }
        scrollToBottom();
    }

    // Append message to UI
    function appendMessage(role, text, save = true) {
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${role}`;
        bubble.textContent = text;
        chatbotMessages.appendChild(bubble);

        if (save) {
            chatHistory.push({ role, content: text });
            sessionStorage.setItem('chatbot_history', JSON.stringify(chatHistory));
        }
        scrollToBottom();
    }

    function scrollToBottom() {
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }

    // Send suggestions
    window.sendSuggestion = function (text) {
        chatbotInput.value = text;
        sendChatMessage();
    };

    // Send chat message to backend
    window.sendChatMessage = async function () {
        const text = chatbotInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        chatbotInput.value = '';

        // Add loading indicator
        const loading = document.createElement('div');
        loading.className = 'chat-bubble assistant italic text-gray-500';
        loading.id = 'chatbot-loading';
        loading.textContent = 'Searching the ledger...';
        chatbotMessages.appendChild(loading);
        scrollToBottom();

        try {
            // Get user_id and cart items from localStorage
            const user = JSON.parse(localStorage.getItem('currentUser') || '{}');
            const cart = JSON.parse(localStorage.getItem('cart') || '[]');

            const cartItemsMapped = cart.map(item => ({
                product_id: parseInt(item.id),
                name: item.name,
                price: parseFloat(item.price),
                quantity: parseInt(item.qty)
            }));

            const response = await fetch(`${API_URL}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: text,
                    history: chatHistory.slice(-10), // Keep last 10 messages
                    user_id: user.id || null,
                    cart_items: cartItemsMapped
                })
            });

            document.getElementById('chatbot-loading').remove();

            if (response.ok) {
                const data = await response.json();
                appendMessage('assistant', data.reply);
            } else {
                appendMessage('assistant', "⚠️ The Bookkeeper is currently occupied. Please try again shortly.");
            }
        } catch (error) {
            const loadEl = document.getElementById('chatbot-loading');
            if (loadEl) loadEl.remove();
            appendMessage('assistant', "⚠️ Network error. Unable to contact the Bookkeeper.");
        }
    };

    // Handle enter key press
    chatbotInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendChatMessage();
        }
    });

    // Helper functions for user layout
    window.updateNavigationHeader = function () {
        const user = JSON.parse(localStorage.getItem('currentUser') || '{}');
        const keeperSection = document.getElementById('sidebar-keeper-profile');
        if (keeperSection) {
            if (user && user.name) {
                keeperSection.innerHTML = `
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 bg-[#ceeace] border border-[#1c1b19] flex items-center justify-center">
                            <span class="material-symbols-outlined text-[#3e5641]">person</span>
                        </div>
                        <div>
                            <p class="font-bold text-[13px] leading-none">${user.name}</p>
                            <p class="text-[11px] text-on-surface-variant uppercase font-semibold">${user.role}</p>
                        </div>
                    </div>
                `;
            } else {
                keeperSection.innerHTML = `
                    <a href="/login.html" class="font-caps text-[11px] text-primary hover:underline flex items-center gap-2">
                        <span class="material-symbols-outlined">login</span> Log In
                    </a>
                `;
            }
        }
    };

    // Initialize layout hooks on page load
    window.addEventListener('DOMContentLoaded', () => {
        window.updateNavigationHeader();
    });
})();
