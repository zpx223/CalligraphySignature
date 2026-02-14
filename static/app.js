const API_BASE = '';  // Same origin - backend serves at /
const OPENAPI_URL = `${API_BASE}/openapi.json`;

const chatList = document.getElementById('chatList');
const messagesEl = document.getElementById('messages');
const emptyState = document.getElementById('emptyState');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const newChatBtn = document.getElementById('newChat');
const modelSelect = document.getElementById('modelSelect');

let chats = loadChats();
let currentChatId = null;
let selectedModel = localStorage.getItem('selectedModel') || 'gpt-5';

function loadChats() {
  try {
    const s = localStorage.getItem('chats');
    return s ? JSON.parse(s) : [];
  } catch {
    return [];
  }
}

function saveChats() {
  localStorage.setItem('chats', JSON.stringify(chats));
}

function generateId() {
  return 'c_' + Date.now() + '_' + Math.random().toString(36).slice(2, 9);
}

function getChatTitle(chat) {
  const first = chat.messages.find(m => m.role === 'user');
  const text = first?.content || '';
  return text.slice(0, 40) + (text.length > 40 ? '…' : '') || 'New chat';
}

function deleteChat(id, e) {
  e?.stopPropagation();
  const idx = chats.findIndex(c => c.id === id);
  if (idx < 0) return;
  const wasActive = currentChatId === id;
  chats.splice(idx, 1);
  if (chats.length === 0) {
    createChat();
  } else if (wasActive) {
    const next = chats[idx] ?? chats[idx - 1] ?? chats[0];
    selectChat(next.id);
  }
  saveChats();
  renderChatList();
}

function renderChatList() {
  chatList.innerHTML = chats.map(c => `
    <li class="${c.id === currentChatId ? 'active' : ''}" data-id="${c.id}">
      <span class="${c.messages.length === 0 ? 'empty-label' : ''}">${getChatTitle(c)}</span>
      <button class="btn-delete-chat" data-id="${c.id}" title="Delete chat" aria-label="Delete chat">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
          <line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>
        </svg>
      </button>
    </li>
  `).join('');
}

function renderMessages(chat) {
  messagesEl.innerHTML = '';
  if (!chat || chat.messages.length === 0) {
    emptyState.style.display = 'flex';
    return;
  }
  emptyState.style.display = 'none';
  chat.messages.forEach(m => {
    appendMessage(m.role, m.content, m.id);
  });
}

function appendMessage(role, content, id) {
  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.dataset.id = id || '';
  const avatar = role === 'user' ? 'You' : 'AI';
  const escaped = content.replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const formatted = escaped.replace(/\n/g, '<br>');
  div.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-content">${formatted}</div>
  `;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addThinkingBubble() {
  const div = document.createElement('div');
  div.className = 'message assistant thinking-bubble';
  div.dataset.thinking = '1';
  div.innerHTML = `
    <div class="message-avatar">AI</div>
    <div class="message-content">
      <div class="thinking"><span></span><span></span><span></span></div>
    </div>
  `;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function removeThinkingBubble() {
  const el = document.querySelector('.thinking-bubble');
  if (el) el.remove();
}

function selectChat(id) {
  currentChatId = id;
  const chat = chats.find(c => c.id === id);
  renderChatList();
  renderMessages(chat);
}

function createChat() {
  const chat = { id: generateId(), messages: [] };
  chats.unshift(chat);
  currentChatId = chat.id;
  saveChats();
  renderChatList();
  renderMessages(chat);
  emptyState.style.display = 'flex';
  return chat;
}

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  let chat = chats.find(c => c.id === currentChatId);
  if (!chat) chat = createChat();

  const userMsg = { id: generateId(), role: 'user', content: text };
  chat.messages.push(userMsg);
  appendMessage('user', text, userMsg.id);
  userInput.value = '';
  userInput.style.height = 'auto';
  sendBtn.disabled = true;
  emptyState.style.display = 'none';

  const thinkingEl = addThinkingBubble();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_message: text, model: selectedModel }),
    });

    const data = await res.json();
    removeThinkingBubble();

    const content = data.content || (data.detail ? String(data.detail) : 'No response.');
    const assistantMsg = { id: generateId(), role: 'assistant', content };
    chat.messages.push(assistantMsg);
    appendMessage('assistant', content, assistantMsg.id);
  } catch (err) {
    removeThinkingBubble();
    const errMsg = `Error: ${err.message}`;
    const assistantMsg = { id: generateId(), role: 'assistant', content: errMsg };
    chat.messages.push(assistantMsg);
    appendMessage('assistant', errMsg, assistantMsg.id);
  }

  saveChats();
  renderChatList();
  sendBtn.disabled = false;
}

userInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

userInput.addEventListener('input', () => {
  sendBtn.disabled = !userInput.value.trim();
  userInput.style.height = 'auto';
  userInput.style.height = Math.min(userInput.scrollHeight, 150) + 'px';
});

sendBtn.addEventListener('click', sendMessage);

newChatBtn.addEventListener('click', () => createChat());

chatList.addEventListener('click', e => {
  const delBtn = e.target.closest('.btn-delete-chat');
  if (delBtn) {
    deleteChat(delBtn.dataset.id, e);
    return;
  }
  const li = e.target.closest('li[data-id]');
  if (li) selectChat(li.dataset.id);
});

async function initModelSelect() {
  try {
    const res = await fetch(`${API_BASE}/models`);
    const data = await res.json();
    const models = data.models || [];
    const validIds = models.map(m => m.id);
    if (!validIds.includes(selectedModel)) selectedModel = validIds[0] || 'gpt-5';
    modelSelect.innerHTML = models.map(m => `<option value="${m.id}" ${m.id === selectedModel ? 'selected' : ''}>${m.name}</option>`).join('');
  } catch {
    modelSelect.innerHTML = '<option value="gpt-5">GPT-5</option>';
  }
  modelSelect.addEventListener('change', () => {
    selectedModel = modelSelect.value;
    localStorage.setItem('selectedModel', selectedModel);
  });
}

if (chats.length === 0) {
  createChat();
} else {
  currentChatId = chats[0].id;
  selectChat(currentChatId);
}
initModelSelect();
