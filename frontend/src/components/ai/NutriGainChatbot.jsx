import { useEffect, useMemo, useRef, useState } from "react";

import { sendAiChatMessage } from "../../services/apiService";
import "./NutriGainChatbot.css";

const DEFAULT_QUESTIONS = [
  "Hôm nay tôi nên ăn thêm gì?",
  "Protein là gì?",
  "Tại sao ngủ quan trọng?",
  "Tăng cân lành mạnh là gì?",
];

const GREETING = {
  id: "greeting",
  role: "assistant",
  text: "Chào bạn, mình là Trợ lý NutriGain. Bạn có thể hỏi mình về thực đơn hôm nay, bữa phụ, protein, giấc ngủ hoặc cách tăng cân lành mạnh.",
};

function createId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function storageKeyFor(userId) {
  return `nutrigain_chat_messages_${userId || "guest"}`;
}

function loadMessages(userId) {
  if (typeof window === "undefined") return [GREETING];
  try {
    const raw = window.localStorage.getItem(storageKeyFor(userId));
    const parsed = raw ? JSON.parse(raw) : null;
    if (Array.isArray(parsed) && parsed.length > 0) {
      return parsed.slice(-30);
    }
  } catch {
    // Ignore corrupted local chat history.
  }
  return [GREETING];
}

function saveMessages(userId, messages) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(storageKeyFor(userId), JSON.stringify(messages.slice(-30)));
  } catch {
    // Local storage can be unavailable in private browsing modes.
  }
}

export default function NutriGainChatbot({ userId }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState(() => loadMessages(userId));
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [conversationId, setConversationId] = useState(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState(DEFAULT_QUESTIONS);
  const messagesEndRef = useRef(null);
  const trimmedInput = input.trim();

  const page = useMemo(() => {
    if (typeof window === "undefined") return "";
    return window.location.pathname || "";
  }, [isOpen]);

  useEffect(() => {
    setMessages(loadMessages(userId));
  }, [userId]);

  useEffect(() => {
    saveMessages(userId, messages);
  }, [messages, userId]);

  useEffect(() => {
    if (!isOpen) return;
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isOpen, isLoading]);

  async function handleSend(text = trimmedInput) {
    const messageText = String(text || "").trim();
    if (!messageText || isLoading) return;

    const userMessage = { id: createId(), role: "user", text: messageText };
    setMessages((current) => [...current, userMessage].slice(-30));
    setInput("");
    setError("");
    setIsLoading(true);

    try {
      const response = await sendAiChatMessage({
        message: messageText,
        conversation_id: conversationId,
        page,
      });
      setConversationId(response?.conversation_id || conversationId);
      if (Array.isArray(response?.suggested_questions) && response.suggested_questions.length > 0) {
        setSuggestedQuestions(response.suggested_questions);
      }
      const assistantMessage = {
        id: createId(),
        role: "assistant",
        text: response?.answer || "Mình chưa có đủ dữ liệu để trả lời chính xác lúc này.",
      };
      setMessages((current) => [...current, assistantMessage].slice(-30));
    } catch (err) {
      console.error("AI chat error:", err);
      setError("Xin lỗi, mình chưa thể trả lời lúc này. Bạn thử lại sau nhé.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    handleSend();
  }

  return (
    <div className="ng-chatbot" aria-live="polite">
      {isOpen ? (
        <section className="ng-chatbot-panel" aria-label="Trợ lý NutriGain">
          <header className="ng-chatbot-header">
            <div>
              <h2>Trợ lý NutriGain</h2>
              <p>Hỏi về thực đơn, bữa phụ và tăng cân lành mạnh</p>
            </div>
            <button type="button" className="ng-chatbot-close" onClick={() => setIsOpen(false)} aria-label="Đóng trợ lý">
              x
            </button>
          </header>

          <div className="ng-chatbot-messages">
            {messages.map((message) => (
              <div key={message.id} className={`ng-chatbot-message ${message.role}`}>
                {message.text}
              </div>
            ))}
            {isLoading ? <div className="ng-chatbot-message assistant pending">Đang trả lời...</div> : null}
            <div ref={messagesEndRef} />
          </div>

          {error ? <div className="ng-chatbot-error">{error}</div> : null}

          <div className="ng-chatbot-quick">
            {suggestedQuestions.map((question) => (
              <button key={question} type="button" onClick={() => handleSend(question)} disabled={isLoading}>
                {question}
              </button>
            ))}
          </div>

          <form className="ng-chatbot-form" onSubmit={handleSubmit}>
            <input
              value={input}
              maxLength={1000}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Hỏi Trợ lý NutriGain..."
              aria-label="Hỏi Trợ lý NutriGain"
            />
            <button type="submit" disabled={!trimmedInput || isLoading}>
              Gửi
            </button>
          </form>
        </section>
      ) : null}

      <button type="button" className="ng-chatbot-sticker" onClick={() => setIsOpen((value) => !value)} aria-expanded={isOpen} aria-label="Mở trợ lý NutriGain" title="Trợ lý NutriGain">
        <span aria-hidden="true" className="ng-chatbot-sticker-icon">🤖</span>
      </button>
    </div>
  );
}
