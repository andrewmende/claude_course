import { useState } from "react";
import ChatView from "./ChatView";
import "./App.css";

export default function App() {
  const [learnerId, setLearnerId] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [input, setInput] = useState("");

  function handleStart(e) {
    e.preventDefault();
    const id = input.trim();
    if (id) {
      setLearnerId(id);
      setConfirmed(true);
    }
  }

  if (!confirmed) {
    return (
      <div className="login">
        <h1>LMS Tutor</h1>
        <form onSubmit={handleStart}>
          <input
            autoFocus
            placeholder="Enter your learner ID"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <button type="submit">Start</button>
        </form>
      </div>
    );
  }

  return (
    <div className="app">
      <header>
        <span className="logo">LMS Tutor</span>
        <span className="learner-id">{learnerId}</span>
      </header>
      <ChatView learnerId={learnerId} />
    </div>
  );
}
