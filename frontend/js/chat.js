// ===== CHAT FUNCTIONALITY: MULTI-SESSION SUPPORT =====

import { generateId, formatTime, parseMarkdown, scrollIntoView, autoResizeTextarea } from './utils.js';

const STORAGE_KEY = 'aria-chat-sessions';

// Chat state
let sessions = [];
let currentSessionId = null;
let isTyping = false;
let firstMessageSent = false;

// DOM elements
let chatMessages, messageInput, sendBtn, typingIndicator, chatForm;

/**
 * Initialize chat functionality
 */
export function initChat() {
  // Get DOM elements
  chatMessages = document.getElementById('chat-messages');
  messageInput = document.getElementById('message-input');
  sendBtn = document.getElementById('send-btn');
  typingIndicator = document.getElementById('typing-indicator');
  chatForm = document.getElementById('chat-form');

  // Set up event listeners
  setupEventListeners();

  // Load sessions from storage
  loadSessions();

  // If no sessions, create the first one
  if (sessions.length === 0) {
    createNewSession();
  } else {
    // Show the most recent session
    setCurrentSession(sessions[sessions.length - 1].id);
  }
}

/**
 * Set up event listeners for chat functionality
 */
function setupEventListeners() {
  // Form submission
  chatForm.addEventListener('submit', handleSendMessage);

  // Auto-resize textarea
  messageInput.addEventListener('input', () => {
    autoResizeTextarea(messageInput);
    updateSendButton();
  });

  // Handle Enter key (send message) and Shift+Enter (new line)
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  });

  // Update send button state on input
  messageInput.addEventListener('input', updateSendButton);
}

/**
 * Handle sending a message
 */
async function handleSendMessage(e) {
  e.preventDefault();

  const content = messageInput.value.trim();
  if (!content || isTyping) return;

  // Create user message
  const userMessage = {
    id: generateId(),
    content,
    role: 'user',
    timestamp: new Date(),
    files: []
  };

  // Add message to chat
  addMessageToCurrentSession(userMessage);

  // Confetti on first message in session
  if (!firstMessageSent) {
    firstMessageSent = true;
    launchConfetti();
  }

  // Clear input
  messageInput.value = '';
  autoResizeTextarea(messageInput);
  updateSendButton();

  // Show typing indicator
  showTypingIndicator();

  // Send message to backend
  try {
    await sendMessageToBackend(userMessage);
  } catch (error) {
    console.error('Failed to send message:', error);
    hideTypingIndicator();
    showErrorMessage('Failed to send message. Please try again.');
  }
}

/**
 * Send message to backend API
 */
async function sendMessageToBackend(message) {
  // Mock API call for now - replace with actual backend endpoint
  const response = await mockApiCall(message);

  hideTypingIndicator();

  // Create assistant response
  const assistantMessage = {
    id: generateId(),
    content: response.content,
    role: 'assistant',
    timestamp: new Date(),
    agent: response.agent || 'aria'
  };

  // Add response to chat
  addMessageToCurrentSession(assistantMessage);
}

/**
 * Mock API call - replace with actual backend integration
 */
async function mockApiCall(message) {
  await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));
  const responses = [
    {
      content: "I understand your question. Let me help you with that. This is a mock response from the AI agent system.",
      agent: "reasoning"
    },
    {
      content: "That's an interesting point! Here's what I think about it based on my analysis and reasoning capabilities.",
      agent: "reasoning"
    },
    {
      content: "I can help you explore this topic further. Would you like me to provide more detailed information or examples?",
      agent: "reasoning"
    }
  ];
  return responses[Math.floor(Math.random() * responses.length)];
}

/**
 * Add a message to the current session
 */
function addMessageToCurrentSession(message) {
  const session = sessions.find(s => s.id === currentSessionId);
  if (!session) return;
  session.messages.push(message);
  saveSessions();
  renderCurrentSession();
  window.dispatchEvent(new Event('aria-message-added'));
}

/**
 * Render messages for the current session
 */
function renderCurrentSession() {
  const session = sessions.find(s => s.id === currentSessionId);
  if (!chatMessages) return;
  chatMessages.innerHTML = '';
  if (!session || session.messages.length === 0) {
    chatMessages.innerHTML = `
      <div class="welcome-message">
        <div class="welcome-content">
          <img src="assets/avatars/aria.png" alt="Aria" class="welcome-avatar">
          <h2>Welcome to Aria</h2>
          <p>Your intelligent AI assistant powered by local models. Experience seamless conversations with advanced reasoning capabilities.</p>
        </div>
      </div>
    `;
    return;
  }
  session.messages.forEach(message => {
    const messageElement = createMessageElement(message);
    chatMessages.appendChild(messageElement);
  });
  // Scroll to bottom
  if (chatMessages.lastChild) scrollIntoView(chatMessages.lastChild);
}

/**
 * Create a message DOM element
 */
function createMessageElement(message) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${message.role}`;
  messageDiv.setAttribute('data-message-id', message.id);

  // Create avatar
  const avatar = document.createElement('img');
  avatar.className = 'message-avatar';
  avatar.alt = message.role === 'user' ? 'User' : 'Assistant';

  if (message.role === 'user') {
    avatar.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMTYiIGN5PSIxNiIgcj0iMTYiIGZpbGw9IiM2MzY2ZjEiLz4KPGNpcmNsZSBjeD0iMTYiIGN5PSIxMiIgcj0iNSIgZmlsbD0id2hpdGUiLz4KPHBhdGggZD0iTTYgMjZjMC01LjUyMyA0LjQ3Ny0xMCAxMC0xMHMxMCA0LjQ3NyAxMCAxMCIgZmlsbD0id2hpdGUiLz4KPC9zdmc+';
  } else {
    avatar.src = 'assets/avatars/aria.png';
  }

  // Create content container
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';

  // Create message bubble
  const bubbleDiv = document.createElement('div');
  bubbleDiv.className = 'message-bubble';
  bubbleDiv.innerHTML = parseMarkdown(message.content);

  // Create message meta
  const metaDiv = document.createElement('div');
  metaDiv.className = 'message-meta';

  const timeSpan = document.createElement('span');
  timeSpan.className = 'message-time';
  timeSpan.textContent = formatTime(message.timestamp);
  metaDiv.appendChild(timeSpan);

  if (message.agent && message.role === 'assistant') {
    const agentSpan = document.createElement('span');
    agentSpan.className = 'message-agent';
    agentSpan.textContent = message.agent;
    metaDiv.appendChild(agentSpan);
  }

  // Assemble message
  contentDiv.appendChild(bubbleDiv);
  contentDiv.appendChild(metaDiv);

  messageDiv.appendChild(avatar);
  messageDiv.appendChild(contentDiv);

  // Add fade-in animation
  messageDiv.classList.add('fade-in');

  return messageDiv;
}

/**
 * Show typing indicator
 */
function showTypingIndicator() {
  isTyping = true;
  typingIndicator.style.display = 'flex';
  // Animate agent avatar (pulse)
  const avatar = typingIndicator.querySelector('.agent-avatar');
  if (avatar) {
    avatar.classList.add('pulse-avatar');
    setTimeout(() => avatar.classList.remove('pulse-avatar'), 1200);
  }
  scrollIntoView(typingIndicator);
  updateSendButton();
}

/**
 * Hide typing indicator
 */
function hideTypingIndicator() {
  isTyping = false;
  typingIndicator.style.display = 'none';
  updateSendButton();
}

/**
 * Update send button state
 */
function updateSendButton() {
  const hasContent = messageInput.value.trim().length > 0;
  sendBtn.disabled = !hasContent || isTyping;
}

/**
 * Show error message
 */
function showErrorMessage(errorText) {
  const errorMessage = {
    id: generateId(),
    content: errorText,
    role: 'system',
    timestamp: new Date()
  };
  addMessageToCurrentSession(errorMessage);
}

/**
 * Load sessions from localStorage
 */
function loadSessions() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      sessions = JSON.parse(saved);
      // Convert timestamps back to Date objects
      sessions.forEach(session => {
        session.messages.forEach(msg => {
          msg.timestamp = new Date(msg.timestamp);
        });
      });
    } else {
      sessions = [];
    }
  } catch (error) {
    sessions = [];
    console.warn('Failed to load chat sessions:', error);
  }
}

/**
 * Save sessions to localStorage
 */
function saveSessions() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch (error) {
    console.warn('Failed to save chat sessions:', error);
  }
}

/**
 * Create a new chat session
 */
export function createNewSession(name = null) {
  const session = {
    id: generateId(),
    name: name || `Session ${sessions.length + 1}`,
    created: new Date(),
    messages: []
  };
  sessions.push(session);
  setCurrentSession(session.id);
  saveSessions();
  window.dispatchEvent(new Event('aria-session-changed'));
}

/**
 * Set the current session by ID
 */
export function setCurrentSession(sessionId) {
  currentSessionId = sessionId;
  firstMessageSent = false;
  renderCurrentSession();
  window.dispatchEvent(new Event('aria-session-changed'));
}

/**
 * Get all sessions
 */
export function getSessions() {
  return sessions.map(s => ({
    id: s.id,
    name: s.name,
    created: s.created,
    messages: s.messages
  }));
}

/**
 * Get the current session ID
 */
export function getCurrentSessionId() {
  return currentSessionId;
}

/**
 * Get messages for the current session
 */
export function getMessages() {
  const session = sessions.find(s => s.id === currentSessionId);
  return session ? [...session.messages] : [];
}

/**
 * Add a message programmatically (for file uploads, etc.)
 */
export function addMessageProgrammatically(message) {
  addMessageToCurrentSession(message);
}

/**
 * Launch confetti animation (simple, uplifting)
 */
function launchConfetti() {
  const confettiContainer = document.createElement('div');
  confettiContainer.style.position = 'fixed';
  confettiContainer.style.left = 0;
  confettiContainer.style.top = 0;
  confettiContainer.style.width = '100vw';
  confettiContainer.style.height = '100vh';
  confettiContainer.style.pointerEvents = 'none';
  confettiContainer.style.zIndex = 9999;

  for (let i = 0; i < 24; i++) {
    const confetti = document.createElement('span');
    confetti.textContent = ['🎉', '✨', '💫', '🌈', '🥳', '🦄'][Math.floor(Math.random() * 6)];
    confetti.style.position = 'absolute';
    confetti.style.left = Math.random() * 100 + 'vw';
    confetti.style.top = '-2rem';
    confetti.style.fontSize = (1.5 + Math.random() * 1.5) + 'rem';
    confetti.style.opacity = 0.85;
    confetti.style.transition = 'transform 1.8s cubic-bezier(.23,1.01,.32,1), opacity 0.6s';
    confetti.style.transform = `translateY(0) rotate(${Math.random() * 360}deg)`;
    setTimeout(() => {
      confetti.style.transform = `translateY(${80 + Math.random() * 15}vh) rotate(${Math.random() * 360}deg)`;
      confetti.style.opacity = 0;
    }, 50 + Math.random() * 200);
    confettiContainer.appendChild(confetti);
  }
  document.body.appendChild(confettiContainer);
  setTimeout(() => {
    confettiContainer.remove();
  }, 2200);
}

// Expose session management for sidebar
window.createNewSession = createNewSession;
window.setCurrentSession = setCurrentSession;
window.getSessions = getSessions;
window.getCurrentSessionId = getCurrentSessionId;
