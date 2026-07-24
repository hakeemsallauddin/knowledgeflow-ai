import { useState, useRef, useEffect } from "react";
import api from "../api/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const initialMessage = [
  {
    sender: "ai",
    text: `# 👋 Welcome to KnowledgeFlow AI

Upload any PDF document and ask questions naturally.

### Try asking:
- Summarize this document
- What are the key skills?
- Extract important information
- Explain this section
`,
    sources: [],
  },
];

function ChatBox() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState(initialMessage);
  const [loading, setLoading] = useState(false);

  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);

  const clearChat = () => {
    setMessages(initialMessage);
  };

  const askQuestion = async () => {
    if (!message.trim() || loading) return;

    const question = message.trim();

    setMessages((prev) => [
      ...prev,
      {
        sender: "user",
        text: question,
      },
    ]);

    setMessage("");
    setLoading(true);

    try {
      const response = await api.post("/qa/chat", {
        message: question,
      });

      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: response.data.answer,
          sources: response.data.sources || [],
        },
      ]);
    } catch (err) {
      console.error(err);

      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: "❌ Unable to generate a response. Please try again.",
          sources: [],
        },
      ]);
    }

    setLoading(false);
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>💬 KnowledgeFlow AI</h2>

        <button
          className="new-chat-btn"
          onClick={clearChat}
        >
          New Chat
        </button>
      </div>

      <div className="messages">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`message ${msg.sender}`}
          >
            <div className="bubble">
              <strong>
                {msg.sender === "user"
                  ? "🙂 You"
                  : "🤖 KnowledgeFlow AI"}
              </strong>

              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.text}
              </ReactMarkdown>

              {msg.sender === "ai" &&
                msg.sources &&
                msg.sources.length > 0 && (
                  <div
                    style={{
                      marginTop: "16px",
                      borderTop: "1px solid #ddd",
                      paddingTop: "10px",
                    }}
                  >
                    <strong>📄 Sources</strong>

                    {msg.sources.map((source, i) => (
                      <div
                        key={i}
                        style={{
                          marginTop: "8px",
                        }}
                      >
                        <div className="source-card">

    📄 {source.filename}

</div>

{source.page !== null && (
    <small>Page {source.page}</small>
)}
                      </div>
                    ))}
                  </div>
                )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message ai">
            <div className="bubble">
              <strong>🤖 KnowledgeFlow AI</strong>

              <div className="thinking-box">

    <div>🔍 Searching document...</div>

    <div>
        🤖 Generating answer
        <span className="dots"></span>
    </div>

</div>
            </div>
          </div>
        )}

        <div ref={bottomRef}></div>
      </div>

      <div className="input-area">
        <textarea
          placeholder="Ask anything about your uploaded document..."
          value={message}
          disabled={loading}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              askQuestion();
            }
          }}
        />

        <button
          onClick={askQuestion}
          disabled={loading}
        >
          {loading ? "Generating..." : "Send"}
        </button>
      </div>
    </div>
  );
}

export default ChatBox;