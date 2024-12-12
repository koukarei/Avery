import { Chat } from "../types/chat";
import { ChatAPI } from "../api/Chat";
import React, { createContext, useState, useContext } from 'react'

type ChatContextType = {
  chat?: Chat;
  loading: boolean;
  fetchChat: (id: number) => Promise<Chat|undefined>;
};

export const ChatContext = createContext({} as ChatContextType);

export const ChatProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const [chat, setChat] = useState<Chat>();
  const [loading, setLoading] = useState<boolean>(false);

  const fetchChat = async (id: number) => {
    setLoading(true);
    let ChatData: Chat | undefined = undefined;
    try {
      ChatData = await ChatAPI.fetchChat(id);
      setChat(ChatData);
    } catch (e) {
      console.log(e);
    }
    setLoading(false);
    return ChatData;
  };

  return (
    <ChatContext.Provider value={{ chat, loading, fetchChat }}>
      {children}
    </ChatContext.Provider>
  );
};