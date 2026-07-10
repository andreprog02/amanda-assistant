import { useState, useRef, useEffect } from "react";
import { AMANDA_PROMPT } from "./prompt";

const API_KEY = import.meta.env.VITE_ANTHROPIC_API_KEY;
const MODEL = import.meta.env.VITE_MODEL || "claude-sonnet-4-6";

function Avatar({ size = 52 }) {
  return (
    <svg viewBox="0 0 200 200" width={size} height={size} xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="skinGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#fde0c8"/>
          <stop offset="100%" stopColor="#f5c9a8"/>
        </linearGradient>
        <linearGradient id="hairGrad" x1="0%" y1="0%" x2="80%" y2="100%">
          <stop offset="0%" stopColor="#e8c36a"/>
          <stop offset="40%" stopColor="#d4a34a"/>
          <stop offset="100%" stopColor="#c48d3a"/>
        </linearGradient>
        <linearGradient id="hairHighlight" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#f0d888" stopOpacity="0.6"/>
          <stop offset="100%" stopColor="#e8c36a" stopOpacity="0"/>
        </linearGradient>
        <linearGradient id="lipGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#e87a7a"/>
          <stop offset="100%" stopColor="#d45c5c"/>
        </linearGradient>
        <linearGradient id="shirtGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#f5f0eb"/>
          <stop offset="100%" stopColor="#e8e0d6"/>
        </linearGradient>
        <radialGradient id="cheekL" cx="50%" cy="50%">
          <stop offset="0%" stopColor="#f4a0a0" stopOpacity="0.35"/>
          <stop offset="100%" stopColor="#f4a0a0" stopOpacity="0"/>
        </radialGradient>
        <radialGradient id="cheekR" cx="50%" cy="50%">
          <stop offset="0%" stopColor="#f4a0a0" stopOpacity="0.35"/>
          <stop offset="100%" stopColor="#f4a0a0" stopOpacity="0"/>
        </radialGradient>
        <clipPath id="circleClip">
          <circle cx="100" cy="100" r="96"/>
        </clipPath>
      </defs>

      {/* Background */}
      <circle cx="100" cy="100" r="98" fill="#f8f4f0"/>
      <circle cx="100" cy="100" r="96" fill="#faf6f2"/>

      <g clipPath="url(#circleClip)">
        {/* Hair back - long flowing */}
        <path d="M48 75 Q42 100 44 140 Q46 170 52 200 L148 200 Q154 170 156 140 Q158 100 152 75 Z" fill="url(#hairGrad)"/>
        {/* Hair back volume */}
        <path d="M44 90 Q38 120 40 155 Q42 180 48 200 L52 200 Q46 170 44 140 Q42 110 48 85 Z" fill="url(#hairHighlight)"/>
        <path d="M152 85 Q158 110 156 140 Q154 170 148 200 L152 200 Q158 180 160 155 Q162 120 156 90 Z" fill="url(#hairHighlight)"/>

        {/* Neck */}
        <path d="M82 148 Q85 162 84 175 L116 175 Q115 162 118 148 Z" fill="url(#skinGrad)"/>
        {/* Neck shadow */}
        <path d="M86 148 Q90 155 100 157 Q110 155 114 148 Q110 152 100 153 Q90 152 86 148 Z" fill="#e8b894" opacity="0.3"/>

        {/* Shoulders / top */}
        <path d="M42 175 Q60 162 84 168 L116 168 Q140 162 158 175 Q165 185 165 200 L35 200 Q35 185 42 175 Z" fill="url(#shirtGrad)"/>
        {/* Collar hint */}
        <path d="M84 168 Q92 178 100 180 Q108 178 116 168 Q108 174 100 175 Q92 174 84 168 Z" fill="#ede6de"/>

        {/* Face */}
        <ellipse cx="100" cy="108" rx="38" ry="44" fill="url(#skinGrad)"/>
        {/* Jaw definition */}
        <path d="M68 115 Q72 145 100 152 Q128 145 132 115" fill="url(#skinGrad)"/>

        {/* Cheek blush */}
        <ellipse cx="74" cy="120" rx="10" ry="7" fill="url(#cheekL)"/>
        <ellipse cx="126" cy="120" rx="10" ry="7" fill="url(#cheekR)"/>

        {/* Eyes - larger, more expressive */}
        {/* Left eye */}
        <ellipse cx="82" cy="105" rx="9" ry="7" fill="white"/>
        <ellipse cx="83" cy="105" rx="6" ry="6" fill="#4a8bbf"/>
        <ellipse cx="83" cy="105" rx="3.5" ry="3.5" fill="#1a3a5c"/>
        <circle cx="85" cy="103" r="1.8" fill="white" opacity="0.9"/>
        <circle cx="80" cy="107" r="0.8" fill="white" opacity="0.5"/>
        {/* Left eyelid line */}
        <path d="M73 100 Q78 96 83 96 Q88 96 92 100" stroke="#8a6a4a" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
        {/* Left lower lash line */}
        <path d="M75 109 Q82 113 90 109" stroke="#8a6a4a" strokeWidth="0.6" fill="none" opacity="0.4"/>
        {/* Left eyelashes */}
        <path d="M73 100 Q71 97 70 95" stroke="#5a3a2a" strokeWidth="1" fill="none" strokeLinecap="round"/>
        <path d="M76 98 Q74 95 74 93" stroke="#5a3a2a" strokeWidth="0.8" fill="none" strokeLinecap="round"/>
        <path d="M80 97 Q79 94 79 92" stroke="#5a3a2a" strokeWidth="0.7" fill="none" strokeLinecap="round"/>

        {/* Right eye */}
        <ellipse cx="118" cy="105" rx="9" ry="7" fill="white"/>
        <ellipse cx="117" cy="105" rx="6" ry="6" fill="#4a8bbf"/>
        <ellipse cx="117" cy="105" rx="3.5" ry="3.5" fill="#1a3a5c"/>
        <circle cx="119" cy="103" r="1.8" fill="white" opacity="0.9"/>
        <circle cx="114" cy="107" r="0.8" fill="white" opacity="0.5"/>
        {/* Right eyelid line */}
        <path d="M108 100 Q112 96 117 96 Q122 96 127 100" stroke="#8a6a4a" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
        {/* Right lower lash line */}
        <path d="M110 109 Q118 113 125 109" stroke="#8a6a4a" strokeWidth="0.6" fill="none" opacity="0.4"/>
        {/* Right eyelashes */}
        <path d="M127 100 Q129 97 130 95" stroke="#5a3a2a" strokeWidth="1" fill="none" strokeLinecap="round"/>
        <path d="M124 98 Q126 95 126 93" stroke="#5a3a2a" strokeWidth="0.8" fill="none" strokeLinecap="round"/>
        <path d="M120 97 Q121 94 121 92" stroke="#5a3a2a" strokeWidth="0.7" fill="none" strokeLinecap="round"/>

        {/* Eyebrows - defined, expressive */}
        <path d="M71 93 Q77 88 85 90 Q88 91 91 92" stroke="#b8884a" strokeWidth="2" fill="none" strokeLinecap="round"/>
        <path d="M109 92 Q112 91 115 90 Q123 88 129 93" stroke="#b8884a" strokeWidth="2" fill="none" strokeLinecap="round"/>

        {/* Nose */}
        <path d="M98 108 Q96 118 94 122 Q97 124 100 125 Q103 124 106 122 Q104 118 102 108" stroke="#deb08a" strokeWidth="0.8" fill="none" opacity="0.5"/>
        <path d="M95 122 Q100 126 105 122" stroke="#deb08a" strokeWidth="0.8" fill="none" strokeLinecap="round" opacity="0.6"/>

        {/* Lips - full, warm smile */}
        {/* Upper lip */}
        <path d="M86 133 Q92 129 100 131 Q108 129 114 133" fill="url(#lipGrad)"/>
        {/* Cupid's bow */}
        <path d="M92 131 Q96 128 100 131 Q104 128 108 131" fill="#e06868" opacity="0.6"/>
        {/* Lower lip */}
        <path d="M86 133 Q92 141 100 143 Q108 141 114 133" fill="url(#lipGrad)"/>
        {/* Lip shine */}
        <ellipse cx="100" cy="137" rx="6" ry="2.5" fill="white" opacity="0.15"/>
        {/* Smile line */}
        <path d="M86 133 Q100 136 114 133" stroke="#c85050" strokeWidth="0.5" fill="none" opacity="0.5"/>

        {/* Hair front - flowing bangs */}
        <path d="M52 68 Q55 50 70 42 Q85 36 100 38 Q115 36 130 42 Q145 50 148 68 Q145 58 135 50 Q122 42 100 40 Q78 42 65 50 Q55 58 52 68 Z" fill="url(#hairGrad)"/>
        {/* Side swept bangs */}
        <path d="M52 68 Q50 55 55 45 Q62 36 75 34 Q65 40 58 50 Q53 60 54 72 Z" fill="url(#hairGrad)"/>
        <path d="M52 68 Q48 58 52 48 Q54 42 60 38 Q52 45 50 55 Q48 62 52 72 Z" fill="url(#hairHighlight)"/>
        {/* Hair strand details */}
        <path d="M60 42 Q65 38 72 36" stroke="#d4a34a" strokeWidth="0.5" fill="none" opacity="0.5"/>
        <path d="M55 50 Q62 44 70 40" stroke="#f0d888" strokeWidth="0.5" fill="none" opacity="0.3"/>

        {/* Right side hair */}
        <path d="M148 68 Q150 55 145 45 Q138 36 125 34 Q135 40 142 50 Q147 60 146 72 Z" fill="url(#hairGrad)"/>

        {/* Hair flowing over shoulders */}
        <path d="M44 140 Q46 155 50 175 Q52 185 48 200 L42 200 Q44 185 42 170 Q40 155 44 140 Z" fill="url(#hairGrad)" opacity="0.9"/>
        <path d="M156 140 Q154 155 150 175 Q148 185 152 200 L158 200 Q156 185 158 170 Q160 155 156 140 Z" fill="url(#hairGrad)" opacity="0.9"/>
      </g>

      {/* Circle border */}
      <circle cx="100" cy="100" r="96" fill="none" stroke="#e8e0d8" strokeWidth="1.5"/>
    </svg>
  );
}

function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 5, padding: "8px 16px", alignItems: "center" }}>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: "#b0b8c1",
            animation: `bounce 1.2s ease-in-out ${i * 0.15}s infinite`,
          }}
        />
      ))}
    </div>
  );
}

export default function AmandaPrototype() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Aiii você veio! ✨ Tava aqui esperando... sério, meu dia ficou melhor agora. Conta, como você tá?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = { role: "user", content: text };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput("");
    setLoading(true);

    try {
      const apiMessages = updatedMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": API_KEY,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model: MODEL,
          max_tokens: 1000,
          system: AMANDA_PROMPT,
          messages: apiMessages,
        }),
      });

      const data = await response.json();
      const reply =
        data.content
          ?.filter((b) => b.type === "text")
          .map((b) => b.text)
          .join("") || "Hmm, me perdi aqui... fala de novo?";

      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Ai, deu um probleminha aqui na conexão... tenta de novo? 🥺" },
      ]);
    }
    setLoading(false);
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#f0ece4",
        display: "flex",
        flexDirection: "column",
        fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
        color: "#2c2c2c",
        maxWidth: 480,
        margin: "0 auto",
      }}
    >
      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
          30% { transform: translateY(-6px); opacity: 1; }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(6px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Header */}
      <div
        style={{
          padding: "14px 16px",
          display: "flex",
          alignItems: "center",
          gap: 12,
          background: "#ffffff",
          borderBottom: "1px solid #e5e0d8",
          position: "sticky",
          top: 0,
          zIndex: 10,
        }}
      >
        <Avatar size={44} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 16, fontWeight: 600, color: "#1a1a1a", lineHeight: 1.2 }}>
            Amanda
          </div>
          <div style={{ fontSize: 12, color: loading ? "#e8915a" : "#6bab72", marginTop: 1 }}>
            {loading ? "digitando..." : "online"}
          </div>
        </div>
      </div>

      {/* Chat area */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px 12px 8px",
          display: "flex",
          flexDirection: "column",
          gap: 6,
          minHeight: 380,
          maxHeight: "68vh",
        }}
      >
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
              animation: "fadeIn 0.25s ease-out",
            }}
          >
            {msg.role === "assistant" && (
              <div style={{ flexShrink: 0, marginRight: 6, marginTop: 4 }}>
                <Avatar size={28} />
              </div>
            )}
            <div
              style={{
                maxWidth: "78%",
                padding: "9px 13px",
                borderRadius:
                  msg.role === "user"
                    ? "18px 18px 4px 18px"
                    : "18px 18px 18px 4px",
                background: msg.role === "user" ? "#d9f0d4" : "#ffffff",
                fontSize: 14.5,
                lineHeight: 1.5,
                color: "#1a1a1a",
                boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
              }}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: "flex", alignItems: "flex-start", animation: "fadeIn 0.25s ease-out" }}>
            <div style={{ flexShrink: 0, marginRight: 6, marginTop: 4 }}>
              <Avatar size={28} />
            </div>
            <div
              style={{
                background: "#ffffff",
                borderRadius: "18px 18px 18px 4px",
                boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
              }}
            >
              <TypingIndicator />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div
        style={{
          padding: "10px 12px 16px",
          background: "#ffffff",
          borderTop: "1px solid #e5e0d8",
        }}
      >
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Fala comigo..."
            disabled={loading}
            style={{
              flex: 1,
              padding: "10px 16px",
              borderRadius: 24,
              border: "1.5px solid #ddd6cc",
              background: "#faf8f4",
              color: "#1a1a1a",
              fontSize: 14.5,
              outline: "none",
              transition: "border-color 0.2s",
            }}
            onFocus={(e) => (e.target.style.borderColor = "#b8a88a")}
            onBlur={(e) => (e.target.style.borderColor = "#ddd6cc")}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            style={{
              width: 40,
              height: 40,
              borderRadius: "50%",
              border: "none",
              background:
                loading || !input.trim() ? "#ddd6cc" : "#6bab72",
              color: "#fff",
              fontSize: 18,
              cursor: loading || !input.trim() ? "default" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.2s",
              flexShrink: 0,
            }}
          >
            ↑
          </button>
        </div>
        <div
          style={{
            textAlign: "center",
            fontSize: 10,
            color: "#b8b0a4",
            marginTop: 8,
            letterSpacing: "0.04em",
          }}
        >
          PROTÓTIPO v0.2 · texto apenas · voz em breve
        </div>
      </div>
    </div>
  );
}
