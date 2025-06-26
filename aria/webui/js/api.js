/**
 * Aria API Service Layer
 * Handles all communication with the FastAPI backend
 */

class AriaAPI {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
    this.timeout = 360000; // 6 minutes in milliseconds
  }

  /**
   * Create an AbortController with timeout
   */
  _createTimeoutController(timeoutMs = this.timeout) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      controller.abort();
    }, timeoutMs);
    
    // Clear timeout if request completes normally
    controller.signal.addEventListener('abort', () => {
      clearTimeout(timeoutId);
    });
    
    return controller;
  }

  /**
   * Make a fetch request with error handling and timeout
   */
  async _fetch(url, options = {}) {
    const fullUrl = `${this.baseUrl}${url}`;
    const controller = this._createTimeoutController();
    
    try {
      const response = await fetch(fullUrl, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        signal: controller.signal,
        ...options
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`API Error ${response.status}: ${errorData.detail || response.statusText}`);
      }

      // Handle 204 No Content responses
      if (response.status === 204) {
        return null;
      }

      return await response.json();
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('Request timed out after 6 minutes. Please try again.');
      }
      console.error('API Request failed:', error);
      throw error;
    }
  }

  // ===== HEALTH CHECK =====

  /**
   * Check API health status
   * GET /api/health
   */
  async healthCheck() {
    return await this._fetch('/api/health');
  }

  // ===== SESSION MANAGEMENT =====

  /**
   * Get all session metadata (lightweight, without messages)
   * GET /api/sessions/metadata
   */
  async getSessionMetadata() {
    return await this._fetch('/api/sessions/metadata');
  }

  /**
   * Create a new session
   * POST /api/sessions
   */
  async createSession(name = null) {
    return await this._fetch('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({ name })
    });
  }


  /**
   * Delete a session
   * DELETE /api/sessions/{sessionId}
   */
  async deleteSession(sessionId) {
    return await this._fetch(`/api/sessions/${sessionId}`, {
      method: 'DELETE'
    });
  }

  // ===== MESSAGE MANAGEMENT =====

  /**
   * Get paginated messages for a session
   * GET /api/sessions/{sessionId}/messages/paginated
   * @param {string} sessionId - The session ID
   * @param {number} limit - Maximum number of messages to return
   * @param {string|null} cursor - Cursor for pagination (timestamp of oldest message in previous page)
   * @returns {Promise<PaginatedMessagesResponse>}
   */
  async getPaginatedMessages(sessionId, limit = 20, cursor = null) {
    let url = `/api/sessions/${sessionId}/messages/paginated?limit=${limit}`;
    if (cursor) {
      url += `&cursor=${encodeURIComponent(cursor)}`;
    }
    return await this._fetch(url);
  }

  /**
   * Send a message and get streaming response
   * POST /api/sessions/{sessionId}/messages
   */
  async sendMessage(sessionId, message, onChunk = null) {
    const response = await fetch(`${this.baseUrl}/api/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            content: message,
            role: 'user',
        }),
    });
    
    // Handle streaming response
    if (onChunk && response.body) {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          fullContent += chunk;
          
          // Call the chunk handler
          if (onChunk) {
            onChunk(chunk, fullContent);
          }
        }
        
        return fullContent;
      } finally {
        reader.releaseLock();
      }
    }

    // Fallback for non-streaming
    return await response.text();
  }

  /**
   * Delete a specific message
   * DELETE /api/sessions/{sessionId}/messages/{messageId}
   */
  async deleteMessage(sessionId, messageId) {
    return await this._fetch(`/api/sessions/${sessionId}/messages/${messageId}`, {
      method: 'DELETE'
    });
  }

  // ===== SEARCH =====

  /**
   * Search messages across sessions
   * GET /api/sessions/search?q={query}
   */
  async searchMessages(query) {
    const encodedQuery = encodeURIComponent(query);
    return await this._fetch(`/api/sessions/search?q=${encodedQuery}`);
  }

  // ===== PASSWORD MANAGEMENT =====

  /**
   * Set or change session password
   * PUT /api/sessions/{sessionId}/password
   */
  async setSessionPassword(sessionId, currentPassword, newPassword) {
    return await this._fetch(`/api/sessions/${sessionId}/password`, {
      method: 'PUT',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword
      })
    });
  }

  /**
   * Remove session password
   * DELETE /api/sessions/{sessionId}/password
   */
  async removeSessionPassword(sessionId, currentPassword) {
    return await this._fetch(`/api/sessions/${sessionId}/password`, {
      method: 'DELETE',
      body: JSON.stringify({
        current_password: currentPassword
      })
    });
  }

  /**
   * Validate session password
   * POST /api/sessions/{sessionId}/validate
   */
  async validateSessionPassword(sessionId, password) {
    return await this._fetch(`/api/sessions/${sessionId}/validate`, {
      method: 'POST',
      body: JSON.stringify({
        password: password
      })
    });
  }

  /**
   * Improve a prompt without changing its original meaning
   * POST /api/improve-prompt
   */
  async improvePrompt(promptText) {
    return await this._fetch('/api/improve-prompt', {
      method: 'POST',
      body: JSON.stringify({
        text: promptText
      })
    });
  }
}

// ===== DATA TRANSFORMATION UTILITIES =====

/**
 * Transform backend SessionResponse to frontend session format
 */
function transformSession(backendSession) {
  return {
    id: backendSession.id,
    name: backendSession.name || `Session ${backendSession.id.slice(0, 8)}`,
    created: new Date(backendSession.created),
    messages: [], // Will be populated separately
    isProtected: backendSession.is_protected || false,
    messageCount: backendSession.message_count || 0,
    userMessageCount: backendSession.user_message_count || 0
  };
}

/**
 * Transform backend SessionMetadataResponse to frontend session format
 */
function transformSessionMetadata(backendSession) {
  return {
    id: backendSession.id,
    name: backendSession.name || `Session ${backendSession.id.slice(0, 8)}`,
    created: new Date(backendSession.created),
    messages: [], // Will be populated separately when needed
    isProtected: backendSession.is_protected || false,
    messageCount: backendSession.message_count || 0,
    userMessageCount: backendSession.user_message_count || 0,
    lastMessageTimestamp: backendSession.last_message_timestamp ? new Date(backendSession.last_message_timestamp) : null,
    lastMessagePreview: backendSession.last_message_preview || null
  };
}

/**
 * Transform backend SessionWithMessages to frontend session format
 */
function transformSessionWithMessages(backendSession) {
  return {
    id: backendSession.id,
    name: backendSession.name || `Session ${backendSession.id.slice(0, 8)}`,
    created: new Date(backendSession.created),
    messages: backendSession.messages.map(transformMessage),
    userMessageCount: backendSession.user_message_count || backendSession.messages.filter(m => m.role === 'user').length || 0
  };
}

/**
 * Transform backend MessageResponse to frontend message format
 */
function transformMessage(backendMessage) {
  return {
    id: backendMessage.id,
    content: backendMessage.content,
    role: backendMessage.role,
    timestamp: new Date(backendMessage.timestamp),
    sessionId: backendMessage.session_id
  };
}

/**
 * Transform backend SearchResponse to frontend format
 */
function transformSearchResult(backendResult) {
  return {
    message: transformMessage(backendResult.message),
    sessionName: backendResult.session_name,
    sessionId: backendResult.session_id
  };
}

// ===== GLOBAL API INSTANCE =====

// Create global API instance
const ariaAPI = new AriaAPI();

// Export for module usage
export { 
  AriaAPI, 
  ariaAPI,
  transformSession,
  transformSessionMetadata,
  transformSessionWithMessages,
  transformMessage,
  transformSearchResult
};

// Make available globally for existing code
window.ariaAPI = ariaAPI;
window.AriaAPI = AriaAPI;
