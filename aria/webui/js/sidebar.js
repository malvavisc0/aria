/* ===== SIDEBAR FUNCTIONALITY: SESSION HISTORY & COLLAPSE ===== */

let searchQuery = '';

export function initSidebar() {
  renderSessionList();
  initSearchBar();
  initNewChatButton();
  window.addEventListener('aria-session-changed', renderSessionList);

  // Sidebar collapse/expand logic
  const sidebar = document.querySelector('.app-sidebar');
  const toggleBtn = document.getElementById('sidebar-toggle-btn');
  
  if (sidebar && toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const isCollapsed = sidebar.getAttribute('data-collapsed') === 'true';
      const newState = !isCollapsed;
      
      sidebar.setAttribute('data-collapsed', newState.toString());
      toggleBtn.classList.toggle('toggled');
      
      // Dispatch event for any listeners
      window.dispatchEvent(new Event('aria-sidebar-toggled'));
      
      // Persist state
      localStorage.setItem('sidebar-collapsed', newState ? '1' : '0');
    });
    
    // Restore state on load
    const savedState = localStorage.getItem('sidebar-collapsed');
    if (savedState === '1') {
      sidebar.setAttribute('data-collapsed', 'true');
      toggleBtn.classList.add('toggled');
    } else {
      sidebar.setAttribute('data-collapsed', 'false');
    }
  }
}

function initNewChatButton() {
  const newChatBtn = document.getElementById('sidebar-new-chat-btn');
  const createNewSession = window.createNewSession;
  
  if (newChatBtn && createNewSession) {
    newChatBtn.onclick = () => createNewSession();
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
      <span class="sidebar-history-session-count">${session.messages.length} msg</span>
    `;
    li.onclick = () => setCurrentSession(session.id);
    list.appendChild(li);
  });
}

// Expose for global use if needed
window.initSidebar = initSidebar;
