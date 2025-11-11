import React, { useState, useEffect, useRef } from 'react';
import './App.css';

export default function App() {
  const [messages, setMessages] = useState([
    { id: 1, role: 'assistant', content: "Hey — I'm your AI bot. Say hi!" }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
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

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    
    const userMsg = { id: Date.now(), role: 'user', content: input.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, userMsg],
          persona: "You are a friendly assistant who answers clearly and briefly."
        })
      });
      
      const data = await res.json();
      if (data.error) {
        setMessages(prev => [...prev, { 
          id: Date.now(), 
          role: 'assistant', 
          content: `Error: ${data.detail?.message || data.detail || 'Something went wrong'}` 
        }]);
      } else {
        setMessages(prev => [...prev, { 
          id: Date.now(), 
          role: 'assistant', 
          content: data.reply 
        }]);
      }
    } catch {
      setMessages(prev => [...prev, { 
        id: Date.now(), 
        role: 'assistant', 
        content: 'Network error. Please check if the backend server is running.' 
      }]);
    }

    setLoading(false);
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
