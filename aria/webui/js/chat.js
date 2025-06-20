// ===== CHAT FUNCTIONALITY: MULTI-SESSION SUPPORT =====

import { generateId, formatTime, parseMarkdown, scrollIntoView, autoResizeTextarea, renderMermaidDiagrams } from './utils.js';
import { ariaAPI, transformSession, transformSessionWithMessages, transformMessage } from './api.js';

const STORAGE_KEY = 'aria-chat-sessions';

// Chat state
let sessions = [];
let currentSessionId = null;
let isTyping = false;
let firstMessageSent = false;
let isLoadingFromAPI = false;

// DOM elements
let chatMessages, messageInput, sendBtn, typingIndicator, chatForm;

// Scrollbar is now completely hidden via CSS, no need for dynamic visibility logic

/**
 * Initialize chat functionality
 */
export async function initChat() {
  // Get DOM elements
  chatMessages = document.getElementById('chat-messages');
  messageInput = document.getElementById('message-input');
  sendBtn = document.getElementById('send-btn');
  chatForm = document.getElementById('chat-form');
  
  // Ensure we have the right container
  if (!chatMessages) {
    chatMessages = document.querySelector('.messages-container');
  }

  // Set up event listeners
  setupEventListeners();

  // Load sessions from backend
  await loadSessions();

  // If no sessions, create the first one
  if (sessions.length === 0) {
    await createNewSession();
  } else {
    // Show the most recent session
    await setCurrentSession(sessions[sessions.length - 1].id);
  }
  
  // Ensure message input is focused
  if (messageInput) {
    // Use a longer timeout to ensure DOM is fully rendered
    setTimeout(() => messageInput.focus(), 800);
    
    // Add a fallback focus attempt after a longer delay
    setTimeout(() => messageInput.focus(), 1500);
  }
  
  // Add click event to the input wrapper to ensure focus
  const inputWrapper = document.querySelector('.input-wrapper');
  if (inputWrapper) {
    inputWrapper.addEventListener('click', () => {
      messageInput.focus();
    });
  }
  
  // Focus the input when the window gains focus
  window.addEventListener('focus', () => {
    if (messageInput) {
      messageInput.focus();
    }
  });
}

/**
 * Set up event listeners for chat functionality
 */
function setupEventListeners() {
  // Form submission
  chatForm.addEventListener('submit', handleSendMessage);

  // Prompt improver button
  const promptImproveBtn = document.getElementById('prompt-improve-btn');
  if (promptImproveBtn) {
    promptImproveBtn.addEventListener('click', handleImprovePrompt);
  }

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
  
  // Add click event to the input wrapper to ensure focus
  const inputWrapper = document.querySelector('.input-wrapper');
  if (inputWrapper) {
    inputWrapper.addEventListener('click', () => {
      messageInput.focus();
    });
  }
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
    // launchConfetti(); // Confetti effect removed
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
  try {
    let assistantContent = '';
    
    // Send message with streaming response
    await ariaAPI.sendMessage(
      currentSessionId,
      message.content,
      message.files || [],
      (chunk, fullContent) => {
        // Update streaming message in real-time
        assistantContent = fullContent;
        updateStreamingMessage(assistantContent);
      }
    );

    // Clean up streaming message
    const streamingElement = document.querySelector('.message.streaming');
    if (streamingElement) {
      streamingElement.remove();
    }

    hideTypingIndicator();

    // Create final assistant response
    const assistantMessage = {
      id: generateId(),
      content: assistantContent,
      role: 'assistant',
      timestamp: new Date(),
      agent: 'aria'
    };

    // Add response to chat
    addMessageToCurrentSession(assistantMessage);
    
    // Refresh session from backend to get the actual stored messages
    await refreshCurrentSession();
    
  } catch (error) {
    console.error('Failed to send message to backend:', error);
    
    // Clean up streaming message on error
    const streamingElement = document.querySelector('.message.streaming');
    if (streamingElement) {
      streamingElement.remove();
    }
    
    hideTypingIndicator();
    showErrorMessage('Failed to send message. Please try again.');
  }
}

/**
 * Update streaming message content in real-time
 */
function updateStreamingMessage(content) {
  // Find or create streaming message element
  let streamingElement = document.querySelector('.message.streaming');
  
  if (!streamingElement) {
    // Create streaming message element
    const streamingMessage = {
      id: 'streaming',
      content: content,
      role: 'assistant',
      timestamp: new Date(),
      agent: 'aria'
    };
    
    streamingElement = createMessageElement(streamingMessage);
    streamingElement.classList.add('streaming');
    chatMessages.appendChild(streamingElement);
  } else {
    // Update existing streaming message
    const bubbleDiv = streamingElement.querySelector('.message-bubble');
    if (bubbleDiv) {
      bubbleDiv.innerHTML = parseMarkdown(content);
      // Render any Mermaid diagrams
      renderMermaidDiagrams(bubbleDiv);
    }
  }
  
  // Scroll to show streaming content
  if (streamingElement) {
    scrollIntoView(streamingElement);
  }
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
          <img src="public/avatars/aria.png" alt="Aria" class="welcome-avatar">
          <h2>Hi there! I'm Aria 🌟</h2>
        </div>
      </div>
      
      <!-- Typing Indicator -->
      <div class="typing-indicator" id="typing-indicator" style="display: none;">
        <div class="typing-avatar">
          <img src="public/avatars/aria.png" alt="Agent" class="agent-avatar">
        </div>
        <div class="typing-content">
          <div class="typing-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    `;
    
    return;
  }
  session.messages.forEach(message => {
    const messageElement = createMessageElement(message);
    chatMessages.appendChild(messageElement);
  });
  
  // Add typing indicator after messages
  const typingIndicatorHTML = `
    <div class="typing-indicator" id="typing-indicator" style="display: none;">
      <div class="typing-avatar">
        <img src="public/avatars/aria.png" alt="Agent" class="agent-avatar">
      </div>
      <div class="typing-content">
        <div class="typing-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  `;
  chatMessages.insertAdjacentHTML('beforeend', typingIndicatorHTML);
  
  // Scroll to bottom
  if (chatMessages && chatMessages.lastChild && chatMessages.lastChild.nodeType === Node.ELEMENT_NODE) {
    scrollIntoView(chatMessages.lastChild);
  }
  
  
}

/**
 * Create a message DOM element
 */
function createMessageElement(message) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${message.role}`;
  messageDiv.setAttribute('data-message-id', message.id);

  // Create content container
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';

  // Create message bubble
  const bubbleDiv = document.createElement('div');
  bubbleDiv.className = 'message-bubble';
  bubbleDiv.innerHTML = parseMarkdown(message.content);
  
  // Render any Mermaid diagrams
  setTimeout(() => renderMermaidDiagrams(bubbleDiv), 100);

  // Create message meta
  const metaDiv = document.createElement('div');
  metaDiv.className = 'message-meta';

  // Add copy button for assistant messages (before timestamp)
  if (message.role === 'assistant') {
    const copyBtn = document.createElement('button');
    copyBtn.className = 'copy-btn-meta';
    copyBtn.title = 'Copy message';
    copyBtn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>
    `;
    
    copyBtn.addEventListener('click', async () => {
      const { copyToClipboard } = await import('./utils.js');
      const success = await copyToClipboard(message.content);
      if (success) {
        copyBtn.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20,6 9,17 4,12"></polyline>
          </svg>
        `;
        setTimeout(() => {
          copyBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
          `;
        }, 2000);
      }
    });
    
    metaDiv.appendChild(copyBtn);
  }

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
  const typingIndicator = document.getElementById('typing-indicator');
  if (typingIndicator) {
    typingIndicator.style.display = 'flex';
    // Animate agent avatar (pulse)
    const avatar = typingIndicator.querySelector('.agent-avatar');
    if (avatar) {
      avatar.classList.add('pulse-avatar');
      setTimeout(() => avatar.classList.remove('pulse-avatar'), 1200);
    }
    if (typingIndicator) {
      scrollIntoView(typingIndicator);
    }
  }
  updateSendButton();
  
  
}

/**
 * Hide typing indicator
 */
function hideTypingIndicator() {
  isTyping = false;
  const typingIndicator = document.getElementById('typing-indicator');
  if (typingIndicator) {
    typingIndicator.style.display = 'none';
  }
  updateSendButton();
  
  
}

/**
 * Update send button state
 */
function updateSendButton() {
  const hasContent = messageInput.value.trim().length > 0;
  sendBtn.disabled = !hasContent || isTyping;
  
  // Add visual enhancement when there's content
  if (hasContent && !isTyping) {
    sendBtn.classList.add('has-content');
  } else {
    sendBtn.classList.remove('has-content');
  }
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
 * Load sessions from backend API
 */
async function loadSessions() {
  if (isLoadingFromAPI) return;
  
  try {
    isLoadingFromAPI = true;
    
    // Get sessions from backend
    const backendSessions = await ariaAPI.getSessions();
    
    // Transform backend sessions to frontend format
    sessions = backendSessions.map(transformSession);
    
    // Cache in localStorage for offline access
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    } catch (error) {
      console.warn('Failed to cache sessions locally:', error);
    }
    
  } catch (error) {
    console.warn('Failed to load sessions from backend, using local cache:', error);
    
    // Fallback to localStorage
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        sessions = JSON.parse(saved);
        // Convert timestamps back to Date objects
        sessions.forEach(session => {
          session.created = new Date(session.created);
          if (session.messages) {
            session.messages.forEach(msg => {
              msg.timestamp = new Date(msg.timestamp);
            });
          }
        });
      } else {
        sessions = [];
      }
    } catch (localError) {
      sessions = [];
      console.warn('Failed to load sessions from local cache:', localError);
    }
  } finally {
    isLoadingFromAPI = false;
  }
}

/**
 * Save sessions to localStorage (cache only)
 */
function saveSessions() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch (error) {
    console.warn('Failed to cache sessions locally:', error);
  }
}

/**
 * Refresh current session from backend
 */
async function refreshCurrentSession() {
  if (!currentSessionId) return;
  
  try {
    const backendSession = await ariaAPI.getSession(currentSessionId);
    const transformedSession = transformSessionWithMessages(backendSession);
    
    // Update local session
    const sessionIndex = sessions.findIndex(s => s.id === currentSessionId);
    if (sessionIndex !== -1) {
      sessions[sessionIndex] = transformedSession;
    }
    
    // Update cache
    saveSessions();
    
    // Re-render current session
    renderCurrentSession();
    
  } catch (error) {
    console.warn('Failed to refresh session from backend:', error);
  }
}

/**
 * Create a new chat session
 */
export async function createNewSession(name = null) {
  try {
    // Create session on backend
    const backendSession = await ariaAPI.createSession(name);
    const newSession = transformSession(backendSession);
    
    // Add to local sessions
    sessions.push(newSession);
    
    // Set as current session
    await setCurrentSession(newSession.id);
    
    // Update cache
    saveSessions();
    window.dispatchEvent(new Event('aria-session-changed'));
    
    return newSession;
  } catch (error) {
    console.error('Failed to create session on backend:', error);
    
    // Fallback to local session creation
    const session = {
      id: generateId(),
      name: name || `Session ${sessions.length + 1}`,
      created: new Date(),
      messages: [],
      userMessageCount: 0
    };
    sessions.push(session);
    setCurrentSession(session.id);
    saveSessions();
    window.dispatchEvent(new Event('aria-session-changed'));
    
    return session;
  }
}

/**
 * Set the current session by ID
 */
export async function setCurrentSession(sessionId) {
  currentSessionId = sessionId;
  firstMessageSent = false;
  
  // Load session details from backend if not already loaded
  const existingSession = sessions.find(s => s.id === sessionId);
  if (!existingSession || !existingSession.messages || existingSession.messages.length === 0) {
    try {
      const backendSession = await ariaAPI.getSession(sessionId);
      const transformedSession = transformSessionWithMessages(backendSession);
      
      // Update local session
      const sessionIndex = sessions.findIndex(s => s.id === sessionId);
      if (sessionIndex !== -1) {
        sessions[sessionIndex] = transformedSession;
      } else {
        sessions.push(transformedSession);
      }
      
      saveSessions();
    } catch (error) {
      console.warn('Failed to load session details from backend:', error);
    }
  }
  
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
    messages: s.messages,
    userMessageCount: s.userMessageCount
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
 * Handle improving the prompt
 */
async function handleImprovePrompt() {
  const content = messageInput.value.trim();
  if (!content || isTyping) return;

  try {
    // Show loading state
    const promptImproveBtn = document.getElementById('prompt-improve-btn');
    if (promptImproveBtn) {
      promptImproveBtn.disabled = true;
      promptImproveBtn.classList.add('loading');
    }

    // Call the API to improve the prompt
    const response = await ariaAPI.improvePrompt(content);
    
    // Update the input with the improved prompt
    if (response && response.improved) {
      messageInput.value = response.improved;
      autoResizeTextarea(messageInput);
      updateSendButton();
      
      // Focus the input
      messageInput.focus();
    }
  } catch (error) {
    console.error('Failed to improve prompt:', error);
    // Show error notification
    showErrorMessage('Failed to improve prompt. Please try again.');
  } finally {
    // Reset button state
    const promptImproveBtn = document.getElementById('prompt-improve-btn');
    if (promptImproveBtn) {
      promptImproveBtn.disabled = false;
      promptImproveBtn.classList.remove('loading');
    }
  }
}
/**
 * Delete a session
 */
export async function deleteSession(sessionId) {
  try {
    // Call backend API to delete session
    await ariaAPI.deleteSession(sessionId);
    
    // Remove session from local sessions array
    const sessionIndex = sessions.findIndex(s => s.id === sessionId);
    if (sessionIndex !== -1) {
      sessions.splice(sessionIndex, 1);
    }
    
    // Handle current session deletion
    if (currentSessionId === sessionId) {
      if (sessions.length > 0) {
        // Switch to the most recent session
        await setCurrentSession(sessions[sessions.length - 1].id);
      } else {
        // Create a new session if no sessions left
        await createNewSession();
      }
    }
    
    // Update cache and notify UI
    saveSessions();
    window.dispatchEvent(new Event('aria-session-changed'));
    
    return true;
  } catch (error) {
    console.error('Failed to delete session:', error);
    throw error;
  }
}

// Confetti effect removed

// Expose session management for sidebar
window.createNewSession = createNewSession;
window.setCurrentSession = setCurrentSession;
window.deleteSession = deleteSession;
window.getSessions = getSessions;
window.getCurrentSessionId = getCurrentSessionId;
