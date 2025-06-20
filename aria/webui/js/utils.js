// ===== UTILITY FUNCTIONS =====

/**
 * Generate a unique ID
 * @returns {string} Unique identifier
 */
export function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

/**
 * Format timestamp to readable time
 * @param {Date|string|number} timestamp 
 * @returns {string} Formatted time string
 */
export function formatTime(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;
  
  // Less than 1 minute
  if (diff < 60000) {
    return 'Just now';
  }
  
  // Less than 1 hour
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000);
    return `${minutes}m ago`;
  }
  
  // Less than 24 hours
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000);
    return `${hours}h ago`;
  }
  
  // More than 24 hours
  return date.toLocaleDateString();
}

/**
 * Format file size to human readable format
 * @param {number} bytes 
 * @returns {string} Formatted size string
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Debounce function calls
 * @param {Function} func 
 * @param {number} wait 
 * @returns {Function} Debounced function
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function calls
 * @param {Function} func 
 * @param {number} limit 
 * @returns {Function} Throttled function
 */
export function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text 
 * @returns {string} Escaped HTML
 */
export function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Parse markdown-like text to HTML
 * @param {string} text 
 * @returns {string} HTML string
 */
export function parseMarkdown(text) {
  if (!text) return '';
  
  // Pre-process Mermaid blocks before markdown-it to avoid HTML escaping
  let processedText = text;
  const mermaidBlocks = [];
  
  // Extract Mermaid blocks and replace with placeholders
  processedText = processedText.replace(/```mermaid\n([\s\S]*?)\n```/g, (match, mermaidCode) => {
    const placeholder = `__MERMAID_BLOCK_${mermaidBlocks.length}__`;
    mermaidBlocks.push(mermaidCode.trim());
    return placeholder;
  });
  
  // Initialize markdown-it
  const md = window.markdownit({
    html: true,
    xhtmlOut: false,
    breaks: true,
    linkify: true,
    typographer: false,
    quotes: '""\'\''
  });
  
  // Render markdown to HTML
  let html = md.render(processedText);
  
  // Restore Mermaid blocks as div containers
  mermaidBlocks.forEach((mermaidCode, index) => {
    const placeholder = `__MERMAID_BLOCK_${index}__`;
    html = html.replace(new RegExp(`<p>${placeholder}</p>`, 'g'), `<div class="mermaid">${mermaidCode}</div>`);
  });
  
  return html;
}


/**
 * Render Mermaid diagrams in a container
 * @param {HTMLElement} container
 */
export async function renderMermaidDiagrams(container) {
  if (!window.mermaid || !container) return;
  
  // Initialize mermaid with proper configuration
  window.mermaid.initialize({
    startOnLoad: false,
    theme: document.body.classList.contains('theme-dark') ? 'dark' : 'default',
    securityLevel: 'loose',
    flowchart: {
      htmlLabels: true,
      curve: 'basis'
    },
    sequence: {
      diagramMarginX: 50,
      diagramMarginY: 10,
      actorMargin: 50,
      width: 150,
      height: 65,
      boxMargin: 10,
      boxTextMargin: 5,
      noteMargin: 10,
      messageMargin: 35
    }
  });
  
  const mermaidElements = container.querySelectorAll('.mermaid');
  if (mermaidElements.length === 0) return;
  
  // Process elements sequentially to avoid ID conflicts
  for (const [index, element] of mermaidElements.entries()) {
    const id = `mermaid-${Date.now()}-${index}`;
    element.id = id;
    
    try {
      // Clean up the content to ensure it's valid Mermaid syntax
      const content = element.textContent.trim();
      
      // Use modern Mermaid v11 async API
      const { svg } = await window.mermaid.render(id, content);
      element.innerHTML = svg;
    } catch (error) {
      console.warn('Failed to render Mermaid diagram:', error);
      element.innerHTML = `<pre><code>${element.textContent}</code></pre>
                          <p class="error-message">Failed to render diagram: ${error.message}</p>`;
    }
  }
}

/**
 * Copy text to clipboard
 * @param {string} text 
 * @returns {Promise<boolean>} Success status
 */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand('copy');
      document.body.removeChild(textArea);
      return true;
    } catch (err) {
      document.body.removeChild(textArea);
      return false;
    }
  }
}

/**
 * Get file type from filename
 * @param {string} filename 
 * @returns {string} File type
 */
export function getFileType(filename) {
  const extension = filename.split('.').pop().toLowerCase();
  
  const imageTypes = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'];
  const documentTypes = ['pdf', 'doc', 'docx', 'txt', 'rtf'];
  const codeTypes = ['js', 'html', 'css', 'json', 'xml', 'py', 'java', 'cpp'];
  
  if (imageTypes.includes(extension)) return 'image';
  if (documentTypes.includes(extension)) return 'document';
  if (codeTypes.includes(extension)) return 'code';
  
  return 'file';
}

/**
 * Get file icon based on file type
 * @param {string} filename 
 * @returns {string} SVG icon string
 */
export function getFileIcon(filename) {
  const type = getFileType(filename);
  
  const icons = {
    image: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
      <circle cx="8.5" cy="8.5" r="1.5"></circle>
      <polyline points="21,15 16,10 5,21"></polyline>
    </svg>`,
    document: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"></path>
    </svg>`,
    code: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <polyline points="16,18 22,12 16,6"></polyline>
      <polyline points="8,6 2,12 8,18"></polyline>
    </svg>`,
    file: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66L9.64 16.2a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
    </svg>`
  };
  
  return icons[type] || icons.file;
}

/**
 * Validate file type and size
 * @param {File} file 
 * @param {Object} options 
 * @returns {Object} Validation result
 */
export function validateFile(file, options = {}) {
  const {
    maxSize = 10 * 1024 * 1024, // 10MB default
    allowedTypes = ['image/*', 'text/*', 'application/pdf']
  } = options;
  
  const errors = [];
  
  // Check file size
  if (file.size > maxSize) {
    errors.push(`File size must be less than ${formatFileSize(maxSize)}`);
  }
  
  // Check file type
  const isAllowed = allowedTypes.some(type => {
    if (type.endsWith('/*')) {
      return file.type.startsWith(type.slice(0, -1));
    }
    return file.type === type;
  });
  
  if (!isAllowed) {
    errors.push('File type not supported');
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Auto-resize textarea based on content
 * @param {HTMLTextAreaElement} textarea 
 */
export function autoResizeTextarea(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

/**
 * Scroll element into view smoothly
 * @param {HTMLElement} element 
 * @param {Object} options 
 */
export function scrollIntoView(element, options = {}) {
  if (!element || typeof element.scrollIntoView !== 'function') {
    console.warn('scrollIntoView: Invalid element provided');
    return;
  }
  
  const {
    behavior = 'smooth',
    block = 'nearest',
    inline = 'nearest'
  } = options;
  
  element.scrollIntoView({
    behavior,
    block,
    inline
  });
}

/**
 * Create a simple event emitter
 * @returns {Object} Event emitter instance
 */
export function createEventEmitter() {
  const events = {};
  
  return {
    on(event, callback) {
      if (!events[event]) {
        events[event] = [];
      }
      events[event].push(callback);
    },
    
    off(event, callback) {
      if (events[event]) {
        events[event] = events[event].filter(cb => cb !== callback);
      }
    },
    
    emit(event, ...args) {
      if (events[event]) {
        events[event].forEach(callback => callback(...args));
      }
    }
  };
}

/**
 * Local storage helpers with error handling
 */
export const storage = {
  get(key, defaultValue = null) {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
      console.warn('Failed to get from localStorage:', error);
      return defaultValue;
    }
  },
  
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (error) {
      console.warn('Failed to set localStorage:', error);
      return false;
    }
  },
  
  remove(key) {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (error) {
      console.warn('Failed to remove from localStorage:', error);
      return false;
    }
  }
};

/**
 * Simple state management
 * @param {Object} initialState 
 * @returns {Object} State manager
 */
export function createState(initialState = {}) {
  let state = { ...initialState };
  const listeners = [];
  
  return {
    get() {
      return { ...state };
    },
    
    set(updates) {
      const prevState = { ...state };
      state = { ...state, ...updates };
      listeners.forEach(listener => listener(state, prevState));
    },
    
    subscribe(listener) {
      listeners.push(listener);
      return () => {
        const index = listeners.indexOf(listener);
        if (index > -1) {
          listeners.splice(index, 1);
        }
      };
    }
  };
}
