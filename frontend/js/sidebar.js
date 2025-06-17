/* ===== SIDEBAR FUNCTIONALITY: SESSION HISTORY & COLLAPSE ===== */

export function initSidebar() {
  renderSessionList();
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

function renderSessionList() {
  const getSessions = window.getSessions;
  const setCurrentSession = window.setCurrentSession;
  const createNewSession = window.createNewSession;
  const getCurrentSessionId = window.getCurrentSessionId;
  if (!getSessions || !setCurrentSession || !createNewSession || !getCurrentSessionId) return;

  const sessions = getSessions();
  const currentSessionId = getCurrentSessionId();
  const list = document.getElementById('chat-history-list');
  if (!list) return;
  list.innerHTML = '';

  // New Chat button
  const newChatBtn = document.createElement('button');
  newChatBtn.className = 'sidebar-new-chat-btn';
  newChatBtn.textContent = '+ New Chat';
  newChatBtn.onclick = () => createNewSession();
  list.appendChild(newChatBtn);

  if (sessions.length === 0) {
    const empty = document.createElement('li');
    empty.className = 'sidebar-history-empty';
    empty.textContent = 'No sessions yet.';
    list.appendChild(empty);
    return;
  }

  sessions.forEach(session => {
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
