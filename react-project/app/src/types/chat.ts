export type Chat = {
    id: number;
    messages?: Message[];
  };
  
export type Message = {
    id: number;
    content: string;
    created_at: Date;
    sender: "user" | "assistant";
};

export type SendMessage = {
    content: string;
    created_at: Date;
};
