/* ===== SIDEBAR FUNCTIONALITY: SESSION HISTORY & COLLAPSE ===== */

let searchQuery = '';

export function initSidebar() {
  renderSessionList();
  initSearchBar();
  initNewChatButton();
  window.addEventListener('aria-session-changed', renderSessionList);

  // Simple sidebar toggle logic
  const sidebar = document.querySelector('.app-sidebar');
  const toggleBtn = document.getElementById('sidebar-toggle-btn');
  const backdrop = document.getElementById('sidebar-backdrop');
  
  if (sidebar && toggleBtn) {
    const toggleSidebar = (collapsed) => {
      sidebar.setAttribute('data-collapsed', collapsed.toString());
      
      // Update ARIA attributes
      toggleBtn.setAttribute('aria-expanded', (!collapsed).toString());
      toggleBtn.setAttribute('aria-label', collapsed ? 'Open sidebar' : 'Close sidebar');
      sidebar.setAttribute('aria-hidden', collapsed.toString());
      
      // Handle backdrop for mobile
      if (backdrop) {
        if (!collapsed && window.innerWidth <= 768) {
          backdrop.classList.add('active');
          document.body.classList.add('sidebar-open');
        } else {
          backdrop.classList.remove('active');
          document.body.classList.remove('sidebar-open');
        }
      }
      
      // Dispatch event
      window.dispatchEvent(new Event('aria-sidebar-toggled'));
      
      // Persist state
      localStorage.setItem('sidebar-collapsed', collapsed ? '1' : '0');
    };
    
    // Click handler
    toggleBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const isCollapsed = sidebar.getAttribute('data-collapsed') === 'true';
      toggleSidebar(!isCollapsed);
    });
    
    // Keyboard support
    toggleBtn.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        const isCollapsed = sidebar.getAttribute('data-collapsed') === 'true';
        toggleSidebar(!isCollapsed);
      }
    });
    
    // Backdrop click to close
    if (backdrop) {
      backdrop.addEventListener('click', () => {
        toggleSidebar(true);
      });
    }
    
    // Window resize handler
    window.addEventListener('resize', () => {
      const isCollapsed = sidebar.getAttribute('data-collapsed') === 'true';
      if (backdrop) {
        if (!isCollapsed && window.innerWidth <= 768) {
          backdrop.classList.add('active');
          document.body.classList.add('sidebar-open');
        } else {
          backdrop.classList.remove('active');
          document.body.classList.remove('sidebar-open');
        }
      }
    });
    
    // Restore state on load
    const savedState = localStorage.getItem('sidebar-collapsed');
    const initialCollapsed = savedState !== '0'; // Default to collapsed
    toggleSidebar(initialCollapsed);
  }
}

function initNewChatButton() {
  const newChatBtn = document.getElementById('sidebar-new-chat-btn');
  const createNewSession = window.createNewSession;
  
  if (newChatBtn && createNewSession) {
    newChatBtn.onclick = async () => {
      try {
        await createNewSession();
      } catch (error) {
        console.error('Failed to create new session:', error);
      }
    };
  }
}

let searchDebounceTimeout;

function initSearchBar() {
  const searchInput = document.getElementById('sidebar-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.toLowerCase();
      clearTimeout(searchDebounceTimeout);
      searchDebounceTimeout = setTimeout(() => {
        renderSessionList();
      }, 300);
    });
  }
}

function renderSessionList() {
  const getSessions = window.getSessions;
  const setCurrentSession = window.setCurrentSession;
  const getCurrentSessionId = window.getCurrentSessionId;
  
  // Wait for functions to be available (prevents race condition)
  if (!getSessions || !setCurrentSession || !getCurrentSessionId) {
    console.warn('Session management functions not yet available, retrying...');
    setTimeout(renderSessionList, 100);
    return;
  }

  const sessions = getSessions();
  const currentSessionId = getCurrentSessionId();
  const list = document.getElementById('chat-history-list');
  if (!list) return;
  list.innerHTML = '';

  // Search input
  const searchContainer = document.createElement('div');
  searchContainer.className = 'sidebar-search-container';
  searchContainer.innerHTML = `
    <input type="text" id="sidebar-search-input" class="sidebar-search-input" placeholder="Search chats..." value="${searchQuery}">
  `;
  list.appendChild(searchContainer);

  // Re-initialize search after DOM update (prevent memory leaks)
  setTimeout(() => {
    // Remove existing listeners first
    const existingInput = document.getElementById('sidebar-search-input');
    if (existingInput && existingInput._searchInitialized) {
      return; // Already initialized, skip
    }
    
    initSearchBar();
    const searchInput = document.getElementById('sidebar-search-input');
    if (searchInput) {
      searchInput._searchInitialized = true; // Mark as initialized
      searchInput.focus();
    }
  }, 0);

  // Filter sessions based on search query
  const filteredSessions = sessions.filter(session => {
    if (!searchQuery) return true;
    
    // Search in session name
    if (session.name.toLowerCase().includes(searchQuery)) return true;
    
    // Search in message content
    return session.messages.some(message =>
      message.content && message.content.toLowerCase().includes(searchQuery)
    );
  });

  if (filteredSessions.length === 0) {
    const empty = document.createElement('li');
    empty.className = 'sidebar-history-empty';
    empty.textContent = searchQuery ? 'No matching chats found.' : 'No sessions yet.';
    list.appendChild(empty);
    return;
  }

  filteredSessions.forEach(session => {
    const li = document.createElement('li');
    li.className = 'sidebar-history-session';
    if (session.id === currentSessionId) li.classList.add('active');
    li.title = new Date(session.created).toLocaleString();
    
    // Create session content div safely
    const sessionContentDiv = document.createElement('div');
    sessionContentDiv.className = 'session-content';
    
    // Create session name span safely (prevents XSS)
    const sessionNameSpan = document.createElement('span');
    sessionNameSpan.className = 'sidebar-history-session-name';
    sessionNameSpan.textContent = session.name; // Safe text insertion
    
    // Create session count span safely
    const sessionCountSpan = document.createElement('span');
    sessionCountSpan.className = 'sidebar-history-session-count';
    sessionCountSpan.textContent = session.userMessageCount || session.messages.filter(m => m.role === 'user').length || 0;
    
    // Create delete button safely
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'session-delete-btn';
    deleteBtn.setAttribute('data-session-id', session.id);
    deleteBtn.setAttribute('aria-label', `Delete session ${session.name}`);
    deleteBtn.setAttribute('title', 'Delete this session');
    deleteBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="3,6 5,6 21,6"></polyline>
        <path d="m19,6v14a2,2 0 0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2,2h4a2,2,0,0,1,2,2v2"></path>
      </svg>
    `;
    
    // Assemble the elements
    sessionContentDiv.appendChild(sessionNameSpan);
    sessionContentDiv.appendChild(sessionCountSpan);
    li.appendChild(sessionContentDiv);
    li.appendChild(deleteBtn);
    
/**
 * Show confirmation dialog for session deletion
 */
async function confirmDeleteSession(sessionId, sessionName) {
  const confirmed = confirm(`Are you sure you want to delete "${sessionName}"?\n\nThis action cannot be undone and will permanently delete all messages in this session.`);
  
  if (confirmed) {
    try {
      const deleteSession = window.deleteSession;
      if (deleteSession) {
        await deleteSession(sessionId);
        showNotification(`Session "${sessionName}" deleted successfully`, 'success');
      } else {
        throw new Error('Delete function not available');
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
      showNotification(`Failed to delete session: ${error.message}`, 'error');
    }
  }
}

/**
 * Show notification message
 */
function showNotification(message, type = 'info') {
  // Create notification element
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  
  // Add to document
  document.body.appendChild(notification);
  
  // Auto remove after 3 seconds
  setTimeout(() => {
    if (notification.parentNode) {
      notification.parentNode.removeChild(notification);
    }
  }, 3000);
}
    // Add click handler for session content (switching sessions)
    const sessionContent = li.querySelector('.session-content');
    sessionContent.onclick = async () => {
      try {
        await setCurrentSession(session.id);
      } catch (error) {
        console.error('Failed to set current session:', error);
      }
    };
    
    // Add click handler for delete button
    const deleteBtnElement = li.querySelector('.session-delete-btn');
    deleteBtnElement.onclick = async (e) => {
      e.stopPropagation();
      await confirmDeleteSession(session.id, session.name);
    };
    
    list.appendChild(li);
  });
}

// Expose for global use if needed
window.initSidebar = initSidebar;
