import React, { useState, useEffect, useRef } from 'react';
import './App.css';

// Backend API configuration
const API_BASE_URL = 'http://localhost:8000';

export default function App() {
  const [messages, setMessages] = useState([
    { id: 1, role: 'assistant', content: "Hey — I'm your AI bot. Say hi!" }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [backendConnected, setBackendConnected] = useState(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  // Check backend connection on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/health`, {
          method: 'GET',
          signal: AbortSignal.timeout(3000) // 3 second timeout
        });
        setBackendConnected(res.ok);
      } catch (error) {
        console.warn('Backend health check failed:', error);
        setBackendConnected(false);
      }
    };
    checkBackend();
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    
    const userMsg = { id: Date.now(), role: 'user', content: input.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      // Format messages for backend API (remove id field, keep only role and content)
      const apiMessages = messages
        .filter(msg => msg.role !== 'system') // Filter out system messages
        .map(msg => ({
          role: msg.role,
          content: msg.content
        }));
      
      // Add the new user message
      apiMessages.push({
        role: 'user',
        content: userMsg.content
      });

      const res = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: apiMessages,
          persona: "You are a friendly assistant who answers clearly and briefly."
        })
      }).catch((fetchError) => {
        // Network error - backend might not be running
        console.error('Fetch error:', fetchError);
        setBackendConnected(false);
        throw new Error(
          `Cannot connect to backend server at ${API_BASE_URL}. ` +
          `Make sure the backend is running. Error: ${fetchError.message}`
        );
      });
      
      if (!res.ok) {
        let errorData;
        try {
          errorData = await res.json();
        } catch {
          errorData = { 
            error: true, 
            detail: { message: `HTTP ${res.status}: ${res.statusText}` } 
          };
        }
        throw new Error(errorData.detail?.message || errorData.detail || `HTTP ${res.status}: ${res.statusText}`);
      }
      
      const data = await res.json();
      
      if (data.error) {
        // Handle error response from backend
        const errorMsg = data.detail?.message || data.detail || 'Something went wrong';
        setMessages(prev => [...prev, { 
          id: Date.now(), 
          role: 'assistant', 
          content: `Error: ${errorMsg}` 
        }]);
      } else if (data.reply) {
        // Success - add assistant reply
        setBackendConnected(true);
        setMessages(prev => [...prev, { 
          id: Date.now(), 
          role: 'assistant', 
          content: data.reply 
        }]);
      } else {
        // Unexpected response format
        setMessages(prev => [...prev, { 
          id: Date.now(), 
          role: 'assistant', 
          content: 'Error: Unexpected response format from server.' 
        }]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, { 
        id: Date.now(), 
        role: 'assistant', 
        content: error.message || 'Network error. Please check if the backend server is running.' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="app-container">
      <div className="chat-header">
        <h1>🤖 AI Chatbot</h1>
        <p>Ask me anything!</p>
        {backendConnected === false && (
          <div style={{ 
            background: '#ff4444', 
            color: 'white', 
            padding: '8px 12px', 
            borderRadius: '4px', 
            fontSize: '14px',
            marginTop: '8px'
          }}>
            ⚠️ Backend server not connected. Make sure it's running on {API_BASE_URL}
          </div>
        )}
        {backendConnected === true && (
          <div style={{ 
            background: '#44ff44', 
            color: 'white', 
            padding: '8px 12px', 
            borderRadius: '4px', 
            fontSize: '14px',
            marginTop: '8px'
          }}>
            ✓ Backend connected
          </div>
        )}
      </div>

      <div className="chat-messages">
        {messages.map(m => (
          <div key={m.id} className={`message ${m.role}`}>
            <div className="message-content">
              {m.role === 'assistant' && <div className="avatar">AI</div>}
              <div className="message-bubble">
                <p>{m.content}</p>
              </div>
              {m.role === 'user' && <div className="avatar user">You</div>}
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="message assistant">
            <div className="message-content">
              <div className="avatar">AI</div>
              <div className="message-bubble loading">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <div className="chat-input-wrapper">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
            rows={1}
            disabled={loading}
            className="chat-input"
          />
          <button 
            onClick={sendMessage} 
            disabled={loading || !input.trim()} 
            className="send-button"
            aria-label="Send message"
          >
            {loading ? (
              <span className="spinner"></span>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
