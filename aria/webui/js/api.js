/**
 * Aria API Service Layer
 * Handles all communication with the FastAPI backend
 */

class AriaAPI {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
  }

  /**
   * Make a fetch request with error handling
   */
  async _fetch(url, options = {}) {
    const fullUrl = `${this.baseUrl}${url}`;
    
    try {
      const response = await fetch(fullUrl, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
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
      console.error('API Request failed:', error);
      throw error;
    }
  }

  /**
   * Make a multipart form request
   */
  async _fetchMultipart(url, formData) {
    const fullUrl = `${this.baseUrl}${url}`;
    
    try {
      const response = await fetch(fullUrl, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`API Error ${response.status}: ${errorData.detail || response.statusText}`);
      }

      return response;
    } catch (error) {
      console.error('Multipart API Request failed:', error);
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
   * Get all sessions
   * GET /api/sessions
   */
  async getSessions() {
    return await this._fetch('/api/sessions');
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
   * Get session with all messages
   * GET /api/sessions/{sessionId}
   */
  async getSession(sessionId) {
    return await this._fetch(`/api/sessions/${sessionId}`);
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
   * Get all messages in a session
   * GET /api/sessions/{sessionId}/messages
   */
  async getMessages(sessionId) {
    return await this._fetch(`/api/sessions/${sessionId}/messages`);
  }

  /**
   * Send a message and get streaming response
   * POST /api/sessions/{sessionId}/messages
   */
  async sendMessage(sessionId, message, files = [], onChunk = null) {
    const formData = new FormData();
    formData.append('message', message);
    formData.append('role', 'user');
    
    // Add files if provided
    files.forEach(file => {
      formData.append('files', file);
    });

    const response = await this._fetchMultipart(`/api/sessions/${sessionId}/messages`, formData);
    
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
    messageCount: backendSession.message_count || 0
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
    messages: backendSession.messages.map(transformMessage)
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
    files: backendMessage.files || [],
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
  transformSessionWithMessages,
  transformMessage,
  transformSearchResult
};

// Make available globally for existing code
window.ariaAPI = ariaAPI;
window.AriaAPI = AriaAPI;