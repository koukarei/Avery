import { Chat, SendMessage } from "../types/chat";
import { authAxios } from "./axios";

export class ChatAPI {

  static async fetchChat(id: number): Promise<Chat> {
    const response = await authAxios.get(`round/${id}/chat/`, {
      headers: sessionStorage.getItem("token")
        ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
        : {},
    });
    return response.data;
  }

  static async sendMessage(id: number,data: SendMessage): Promise<Chat> {
    const response = await authAxios.put(`round/${id}/chat/`, data, {
      headers: sessionStorage.getItem("token")
        ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
        : {},
    });
    return response.data;
  }
}