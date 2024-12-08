import { Leaderboard, LeaderboardListParams, LeaderboardRecommendParams, SubmitLeaderboard } from "../types/leaderboard";
import { authAxios } from "./axios";

export class LeaderboardAPI {
  static async fetchLeaderboardList(params: LeaderboardListParams): Promise<Leaderboard[]> {
    const response = await authAxios.get("Leaderboards/", {
      params: params,
      paramsSerializer: { indexes: null },
      headers: sessionStorage.getItem("token")
        ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
        : {},
    });
    return response.data;
  }

  static async fetchLeaderboardDetail(id: number): Promise<Leaderboard> {
    const response = await authAxios.get(`Leaderboards/${id}/`, {
      headers: sessionStorage.getItem("token")
        ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
        : {},
    });
    return response.data;
  }

  static async createLeaderboard(data: SubmitLeaderboard): Promise<Leaderboard> {
    const response = await authAxios.post(`Leaderboards/`, data, {
      headers: sessionStorage.getItem("token")
        ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
        : {},
    });
    return response.data;
  }

  static async deleteLeaderboard(id: number): Promise<void> {
    await authAxios.delete(`Leaderboards/${id}/`, {
      headers: sessionStorage.getItem("token")
        ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
        : {},
    });
  }

  static async publishLeaderboard(id: number): Promise<void> {
    await authAxios.post(
      `Leaderboards/${id}/publish/`,
      {},
      {
        headers: sessionStorage.getItem("token")
          ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
          : {},
      }
    );
  }

  static async like(id: number): Promise<void> {
    await authAxios.post(
      `Leaderboards/${id}/like/`,
      {},
      {
        headers: sessionStorage.getItem("token")
          ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
          : {},
      }
    ).catch(() => { });
  }

  static async unlike(id: number): Promise<void> {
    await authAxios.post(
      `Leaderboards/${id}/unlike/`,
      {},
      {
        headers: sessionStorage.getItem("token")
          ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
          : {},
      }
    ).catch(() => { });
  }

  static async fetchLeaderboardRecommend(params: LeaderboardRecommendParams): Promise<Leaderboard[]> {
    const response = await authAxios.get(`Leaderboards/recommend/`, {
      params: params,
      headers: sessionStorage.getItem("token")
        ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
        : {},
    });
    return response.data;
  }
}