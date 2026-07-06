import React, { useState } from 'react';

export default function ChatBox() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text: userText }]);
    setLoading(true);

    try {
      const apiBase = process.env.REACT_APP_API_URL || 'http://localhost:3001';
      const response = await fetch(`${apiBase}/api/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: userText }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const resData = await response.json();
      if (resData.success && resData.data) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'bot',
            text: resData.data.answer,
            source: resData.data.source,
          },
        ]);
      } else {
        throw new Error(resData.error || 'Server error');
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          text: `Error: ${err.message}`,
          source: 'fallback',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full justify-end border-t border-slate-700 pt-4 mt-auto">
      <h3 className="text-sm font-semibold text-gray-400 mb-2">Ask BloodIQ</h3>
      
      {/* Messages area */}
      <div className="max-h-48 overflow-y-auto space-y-2 mb-3 pr-1 flex flex-col">
        {messages.length === 0 && (
          <p className="text-xs text-gray-500 italic text-center py-2">
            Ask about shortage alerts, rarer blood types, or donor information...
          </p>
        )}
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex flex-col max-w-[85%] ${
              msg.role === 'user' ? 'self-end items-end' : 'self-start items-start'
            }`}
          >
            <div
              className={`rounded px-3 py-1.5 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-red-900 text-white'
                  : 'bg-slate-700 text-gray-200'
              }`}
            >
              {msg.text}
            </div>
            {msg.role === 'bot' && (
              <span
                className={`text-[10px] uppercase font-bold mt-1 px-1.5 py-0.5 rounded text-white ${
                  msg.source === 'gemini' ? 'bg-blue-800' : 'bg-gray-700'
                }`}
              >
                {msg.source || 'Fallback'}
              </span>
            )}
          </div>
        ))}
        {loading && (
          <div className="self-start text-xs text-gray-400 italic">Thinking...</div>
        )}
      </div>

      {/* Input Form */}
      <form onSubmit={handleSend} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          className="bg-slate-800 border border-slate-600 text-white text-sm rounded px-2.5 py-1.5 flex-1 focus:outline-none focus:border-red-500"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-red-600 hover:bg-red-700 text-white text-sm font-semibold px-3 py-1.5 rounded transition duration-200 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
