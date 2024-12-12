import React from 'react';
import { useState } from "react";
import { Container, Box } from '@mui/material';
/** @jsxImportSource @emotion/react */
import { css } from "@emotion/react";
import { Theme } from '@mui/material';

// Define the props type
interface ChatBoxProps {
  robot: string; // Specify that robot is a string prop
  access_token: string;

}

export default function Chat_Box({ robot, access_token }: ChatBoxProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);

  const handleSubmit = async () => {
    if (!input) return;
    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);

    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json",
        "Authorization": ""
       },
      body: JSON.stringify({ message: input }),
    });
    const data = await response.json();
    const botMessage = { role: "bot", content: data.response };
    setMessages((prev) => [...prev, botMessage]);

    setInput("");
  };

  return (
    <Box>
        <Container css={ConversationStyle}>
        <div style={{ padding: "2rem", fontFamily: "Arial, sans-serif" }}>
        <div style={{ border: "1px solid #ccc", padding: "1rem", marginBottom: "1rem" }}>
            {messages.map((msg, index) => (
            <p key={index}>
                <strong>{msg.role === "user" ? "You" : "AI"}:</strong> {msg.content}
            </p>
            ))}
        </div>
        <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Enter your message"
            style={{ width: "80%", marginRight: "1rem" }}
        />
        <button onClick={handleSubmit} style={{ padding: "0.5rem 1rem" }}>
            Send
        </button>
        
        </div>
        </Container>
        
        <img src={robot} className="Robot" alt="robot" />
    </Box>
  );
}

const ConversationStyle = css`
  bottom: 0%;
  left:20vw;
  width: min-content;
  position: absolute;
`