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
  if (!getSessions || !setCurrentSession || !getCurrentSessionId) return;

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

  // Re-initialize search after DOM update
  setTimeout(() => {
    initSearchBar();
    const searchInput = document.getElementById('sidebar-search-input');
    if (searchInput) searchInput.focus();
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
    li.innerHTML = `
      <span class="sidebar-history-session-name">${session.name}</span>
      <span class="sidebar-history-session-count">${session.userMessageCount}</span>
    `;
    li.onclick = async () => {
      try {
        await setCurrentSession(session.id);
      } catch (error) {
        console.error('Failed to set current session:', error);
      }
    };
    list.appendChild(li);
  });
}

// Expose for global use if needed
window.initSidebar = initSidebar;
