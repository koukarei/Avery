// import { Spot } from "./spot";
// import { User } from "./user";

export type Leaderboard = {
  id: number;
//   user?: User;
  title: string;
  description: string;
  rank?: number;
  post_count: number;
  good_count?: number;
  liked?: boolean;
  is_draft?: boolean;
//   spots?: Spot[];
  post_locations?: [number, number][];
  created_at: Date;
};

export type SubmitLeaderboard = {
  user: number;
  title: string;
  description: string;
  latitude: number;
  longitude: number;
  trip_time: number;
  is_draft: boolean;
};

export type LeaderboardListParams = {
  search?: string[];
  draft?: boolean;
  user_id?: number;
  similar_to?: number;
};

export type LeaderboardRecommendParams = {
  latitude: number;
  longitude: number;
  limit?: number;
};