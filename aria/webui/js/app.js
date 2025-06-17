// ===== MAIN APPLICATION =====

import { initChat } from './chat.js';
import { initUpload } from './upload.js';
import { initSidebar } from './sidebar.js';
import { storage } from './utils.js';
import { ariaAPI } from './api.js';

let currentTheme = 'light';

/**
 * Initialize the application
 */
async function init() {
  console.log('🚀 Initializing Aria Frontend...');

  try {
    // Initialize theme
    initTheme();

    // Check API health
    try {
      const health = await ariaAPI.healthCheck();
      console.log('🏥 API Health:', health);
      showNotification('Connected to backend', 'success', 2000);
    } catch (error) {
      console.warn('⚠️ API health check failed:', error);
      showNotification('Backend connection failed - using offline mode', 'warning', 3000);
    }

    // Initialize chat functionality (async)
    await initChat();

    // Initialize file upload
    initUpload();

    // Initialize sidebar
    initSidebar();

    // Set up global event listeners
    setupGlobalEventListeners();

    console.log('✅ Aria Frontend initialized successfully');
  } catch (error) {
    console.error('❌ Failed to initialize Aria Frontend:', error);
    handleError(error, 'Initialization');
  }
}

/**
 * Initialize sidebar toggle functionality
 */
function initSidebarToggle() {
  // Sidebar toggle is now handled by sidebar.js
  // This function is kept for compatibility but does nothing
  console.log('🔍 Sidebar toggle handled by sidebar.js module');
}

/**
 * Initialize theme system
 */
function initTheme() {
  // Load saved theme or detect system preference
  const savedTheme = storage.get('aria-theme');
  const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  
  currentTheme = savedTheme || systemTheme;
  applyTheme(currentTheme);
  
  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!storage.get('aria-theme')) {
      currentTheme = e.matches ? 'dark' : 'light';
      applyTheme(currentTheme);
    }
  });
}

/**
 * Apply theme to the document
 */
function applyTheme(theme) {
  document.body.className = `theme-${theme}`;
  currentTheme = theme;
  
  // Update theme toggle button state
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.setAttribute('aria-label', `Switch to ${theme === 'light' ? 'dark' : 'light'} theme`);
  }
}

/**
 * Toggle between light and dark themes
 */
function toggleTheme() {
  const newTheme = currentTheme === 'light' ? 'dark' : 'light';
  applyTheme(newTheme);
  storage.set('aria-theme', newTheme);
}

/**
 * Set up global event listeners
 */
function setupGlobalEventListeners() {
  // Theme toggle
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
  }
  
  // Keyboard shortcuts
  document.addEventListener('keydown', handleKeyboardShortcuts);
  
  // Handle visibility change (tab focus/blur)
  document.addEventListener('visibilitychange', handleVisibilityChange);
  
  // Handle window resize
  window.addEventListener('resize', handleWindowResize);
  
  // Handle online/offline status
  window.addEventListener('online', handleOnlineStatus);
  window.addEventListener('offline', handleOfflineStatus);
}

/**
 * Handle keyboard shortcuts
 */
function handleKeyboardShortcuts(e) {
  // Ctrl/Cmd + K: Focus message input
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    const messageInput = document.getElementById('message-input');
    if (messageInput) {
      messageInput.focus();
    }
  }
  
  // Ctrl/Cmd + Shift + L: Toggle theme
  if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'L') {
    e.preventDefault();
    toggleTheme();
  }
  
  // Escape: Clear focus
  if (e.key === 'Escape') {
    document.activeElement?.blur();
  }
}

/**
 * Handle visibility change (tab focus/blur)
 */
function handleVisibilityChange() {
  if (document.hidden) {
    // Tab is hidden
    console.log('📱 Tab hidden');
  } else {
    // Tab is visible
    console.log('👁️ Tab visible');
  }
}

/**
 * Handle window resize
 */
function handleWindowResize() {
  // Update any responsive elements if needed
  // This is a placeholder for future responsive functionality
}

/**
 * Handle online status
 */
function handleOnlineStatus() {
  console.log('🌐 Back online');
  showConnectionStatus('online');
}

/**
 * Handle offline status
 */
function handleOfflineStatus() {
  console.log('📴 Gone offline');
  showConnectionStatus('offline');
}

/**
 * Show connection status
 */
function showConnectionStatus(status) {
  // Remove existing status indicators
  const existingStatus = document.querySelector('.connection-status');
  if (existingStatus) {
    existingStatus.remove();
  }
  
  // Only show status for offline
  if (status === 'offline') {
    const statusDiv = document.createElement('div');
    statusDiv.className = 'connection-status';
    statusDiv.style.cssText = `
      position: fixed;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      background-color: var(--warning);
      color: white;
      padding: var(--spacing-sm) var(--spacing-md);
      border-radius: var(--border-radius);
      box-shadow: var(--shadow-lg);
      z-index: var(--z-toast);
      font-size: var(--text-sm);
      font-weight: var(--font-medium);
    `;
    statusDiv.textContent = '📴 You are offline';
    document.body.appendChild(statusDiv);
  }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info', duration = 3000) {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: var(--spacing-md);
    border-radius: var(--border-radius);
    box-shadow: var(--shadow-lg);
    z-index: var(--z-toast);
    max-width: 300px;
    font-size: var(--text-sm);
    animation: slideInRight 0.3s ease-out;
  `;
  
  // Set colors based on type
  const colors = {
    info: { bg: 'var(--info)', color: 'white' },
    success: { bg: 'var(--success)', color: 'white' },
    warning: { bg: 'var(--warning)', color: 'white' },
    error: { bg: 'var(--error)', color: 'white' }
  };
  
  const color = colors[type] || colors.info;
  notification.style.backgroundColor = color.bg;
  notification.style.color = color.color;
  notification.textContent = message;
  
  document.body.appendChild(notification);
  
  // Remove after duration
  setTimeout(() => {
    if (notification.parentNode) {
      notification.style.animation = 'slideOutRight 0.3s ease-in';
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
      }, 300);
    }
  }, duration);
}

/**
 * Handle errors globally
 */
function handleError(error, context = 'Unknown') {
  console.error(`Error in ${context}:`, error);
  showNotification(`An error occurred: ${error.message}`, 'error');
}

/**
 * Get application info
 */
function getAppInfo() {
  return {
    name: 'Aria',
    version: '2.0.0',
    theme: currentTheme,
    userAgent: navigator.userAgent,
    online: navigator.onLine,
    timestamp: new Date().toISOString()
  };
}

// Global error handler
window.addEventListener('error', (e) => {
  handleError(e.error, 'Global');
});

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', (e) => {
  handleError(e.reason, 'Promise');
  e.preventDefault();
});

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
  @keyframes slideInRight {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  
  @keyframes slideOutRight {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(100%);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);

// Export functions for global access
window.aria = {
  toggleTheme,
  showNotification,
  getAppInfo,
  handleError
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM loaded, initializing...');
    init();
  });
} else {
  console.log('📄 DOM already ready, initializing...');
  // Add a small delay to ensure all elements are rendered
  setTimeout(init, 100);
}
