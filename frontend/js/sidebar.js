/* ===== SIDEBAR FUNCTIONALITY: SESSION HISTORY & COLLAPSE ===== */

export function initSidebar() {
  renderSessionList();
  window.addEventListener('aria-session-changed', renderSessionList);

  // Sidebar collapse/expand logic
  const sidebar = document.querySelector('.main-sidebar');
  const toggleBtn = document.getElementById('sidebar-toggle-btn');
  if (sidebar && toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('sidebar-collapsed');
      toggleBtn.classList.toggle('toggled');
      // Optionally: persist state
      if (sidebar.classList.contains('sidebar-collapsed')) {
        localStorage.setItem('sidebar-collapsed', '1');
      } else {
        localStorage.removeItem('sidebar-collapsed');
      }
    });
    // Restore state on load
    if (localStorage.getItem('sidebar-collapsed') === '1') {
      sidebar.classList.add('sidebar-collapsed');
      toggleBtn.classList.add('toggled');
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
  const list = document.getElementById('sidebar-history-list');
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
