import { useState, useEffect, useRef, useCallback } from "react";
import "./ChatView.css";

const WS_URL = (learnerId) => `ws://localhost:8000/ws/${learnerId}`;

export default function ChatView({ learnerId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const wsRef = useRef(null);
  const bottomRef = useRef(null);

  // Open a persistent WebSocket and attach a single onmessage handler
  useEffect(() => {
    const ws = new WebSocket(WS_URL(learnerId));
    wsRef.current = ws;

    ws.onmessage = (e) => {
      const event = JSON.parse(e.data);

      if (event.type === "text_delta") {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant") {
            updated[updated.length - 1] = { ...last, text: last.text + event.text };
          }
          return updated;
        });

      } else if (event.type === "done") {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant") {
            updated[updated.length - 1] = { ...last, streaming: false };
          }
          return updated;
        });
        setBusy(false);

      } else if (event.type === "notification") {
        setMessages((prev) => [...prev, { role: "notification", text: event.text }]);

      } else if (event.type === "error") {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant") {
            updated[updated.length - 1] = {
              ...last,
              text: `Error: ${event.message}`,
              streaming: false,
              error: true,
            };
          }
          return updated;
        });
        setBusy(false);
      }
    };

    return () => ws.close();
  }, [learnerId]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(() => {
    const text = input.trim();
    const ws = wsRef.current;
    if (!text || busy || !ws || ws.readyState !== WebSocket.OPEN) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", text },
      { role: "assistant", text: "", streaming: true },
    ]);
    setInput("");
    setBusy(true);
    ws.send(JSON.stringify({ content: text }));
  }, [input, busy]);

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="chat">
      <div className="messages">
        {messages.length === 0 && (
          <p className="empty">Say hi to get started!</p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}${msg.error ? " error" : ""}`}>
            <div className="bubble">
              {msg.text || (msg.streaming ? <span className="cursor" /> : "")}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="input-bar">
        <textarea
          rows={1}
          placeholder="Type a message…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={busy}
        />
        <button onClick={sendMessage} disabled={busy || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
