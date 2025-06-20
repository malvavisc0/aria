// ===== MAIN APPLICATION =====

import { initChat } from './chat.js';
import { initUpload } from './upload.js';
import { initSidebar } from './sidebar.js';
import { storage } from './utils.js';
import { ariaAPI } from './api.js';
import './nameGenerator.js'; // Import name generator for global availability

let currentTheme = 'light';

/**
 * Initialize the application
 */
async function init() {
  console.log('🚀 Initializing Aria Frontend...');

  try {
    // Initialize theme
    initTheme();

    // Initialize Mermaid
    initMermaid();

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
 * Initialize Mermaid for diagram rendering with enhanced error handling
 */
function initMermaid() {
  console.log('🔍 MERMAID: Checking library availability...');
  
  // Check if mermaid is available
  if (!window.mermaid) {
    console.warn('⚠️ MERMAID: Library not yet loaded, will retry...');
    
    // Set up a retry mechanism
    let retryCount = 0;
    const maxRetries = 50; // 5 seconds with 100ms intervals
    
    const checkMermaid = setInterval(() => {
      retryCount++;
      
      if (window.mermaid) {
        console.log('✅ MERMAID: Library loaded after', retryCount * 100, 'ms');
        clearInterval(checkMermaid);
        performMermaidInitialization();
      } else if (retryCount >= maxRetries) {
        console.error('❌ MERMAID: Library failed to load after', maxRetries * 100, 'ms');
        clearInterval(checkMermaid);
        showMermaidLoadError();
      }
    }, 100);
    
    return;
  }
  
  performMermaidInitialization();
}

/**
 * Perform the actual mermaid initialization
 */
function performMermaidInitialization() {
  try {
    const theme = currentTheme === 'dark' ? 'dark' : 'default';
    
    window.mermaid.initialize({
      theme: theme,
      startOnLoad: false,
      fontFamily: 'Inter, system-ui, sans-serif',
      fontSize: 13,
      securityLevel: 'loose',
      flowchart: {
        htmlLabels: true,
        curve: 'basis',
        useMaxWidth: false,
        padding: 5,
        nodeSpacing: 25,
        rankSpacing: 30,
        diagramPadding: 8
      },
      sequence: {
        diagramMarginX: 20,
        diagramMarginY: 8,
        actorMargin: 30,
        width: 120,
        height: 50,
        boxMargin: 6,
        boxTextMargin: 3,
        noteMargin: 8,
        messageMargin: 20,
        useMaxWidth: false,
        wrap: true,
        mirrorActors: false,
        bottomMarginAdj: 1
      },
      gantt: {
        useMaxWidth: false,
        leftPadding: 75,
        gridLineStartPadding: 35,
        fontSize: 11,
        sectionFontSize: 12
      },
      journey: {
        useMaxWidth: false,
        diagramMarginX: 20,
        diagramMarginY: 10
      },
      gitgraph: {
        useMaxWidth: false,
        diagramPadding: 8
      },
      classDiagram: {
        useMaxWidth: false,
        diagramPadding: 10
      },
      stateDiagram: {
        useMaxWidth: false,
        diagramPadding: 8
      }
    });
    
    console.log('✅ MERMAID: Initialized successfully with theme:', theme);
    
    // Test mermaid functionality
    testMermaidFunctionality();
    
  } catch (error) {
    console.error('❌ MERMAID: Initialization failed:', error);
    showMermaidInitError(error);
  }
}

/**
 * Test basic mermaid functionality
 */
async function testMermaidFunctionality() {
  try {
    const testDiagram = 'graph TD; A-->B;';
    const testId = 'mermaid-test-' + Date.now();
    
    const result = await window.mermaid.render(testId, testDiagram);
    
    if (result && result.svg) {
      console.log('✅ MERMAID: Functionality test passed');
    } else {
      throw new Error('No SVG generated in test');
    }
  } catch (error) {
    console.error('❌ MERMAID: Functionality test failed:', error);
  }
}

/**
 * Show error when mermaid fails to load
 */
function showMermaidLoadError() {
  console.error('❌ MERMAID: Failed to load library from CDN');
  showNotification('Mermaid diagram library failed to load. Diagrams may not render correctly.', 'warning', 5000);
}

/**
 * Show error when mermaid initialization fails
 */
function showMermaidInitError(error) {
  console.error('❌ MERMAID: Initialization error:', error);
  showNotification('Mermaid diagram initialization failed. Some diagrams may not render.', 'warning', 5000);
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
  
  // Update Mermaid theme
  if (window.mermaid) {
    console.log('🔍 MERMAID: Updating theme to:', theme);
    performMermaidInitialization();
    
    // Re-render any existing diagrams with new theme
    const existingDiagrams = document.querySelectorAll('.mermaid svg');
    if (existingDiagrams.length > 0) {
      console.log(`🔍 MERMAID: Re-rendering ${existingDiagrams.length} existing diagrams with new theme`);
      
      // Import and use the renderMermaidDiagrams function
      import('./mermaid_fix.js').then(({ renderMermaidDiagrams }) => {
        const containers = new Set();
        existingDiagrams.forEach(svg => {
          const container = svg.closest('.message-bubble, .messages-container, .chat-messages');
          if (container) {
            containers.add(container);
          }
        });
        
        containers.forEach(container => {
          renderMermaidDiagrams(container).catch(error => {
            console.warn('Failed to re-render diagrams after theme change:', error);
          });
        });
      });
    }
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
    padding: var(--space-4);
    border-radius: var(--radius-base);
    box-shadow: var(--shadow-lg);
    z-index: var(--z-toast);
    max-width: 300px;
    font-size: var(--text-sm);
    animation: slideInRight 0.3s ease-out;
  `;
  
  // Set colors based on type using theme variables
  switch(type) {
    case 'info':
      notification.style.backgroundColor = 'var(--notification-info-bg)';
      notification.style.color = 'var(--notification-info-text)';
      break;
    case 'success':
      notification.style.backgroundColor = 'var(--notification-success-bg)';
      notification.style.color = 'var(--notification-success-text)';
      break;
    case 'warning':
      notification.style.backgroundColor = 'var(--notification-warning-bg)';
      notification.style.color = 'var(--notification-warning-text)';
      break;
    case 'error':
      notification.style.backgroundColor = 'var(--notification-error-bg)';
      notification.style.color = 'var(--notification-error-text)';
      break;
    default:
      notification.style.backgroundColor = 'var(--notification-info-bg)';
      notification.style.color = 'var(--notification-info-text)';
  }
  
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
