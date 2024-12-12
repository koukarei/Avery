import React, { createContext, useState } from "react";
import { Leaderboard, LeaderboardListParams } from "../types/leaderboard";
import { LeaderboardAPI } from "../api/Leaderboard";

type LeaderboardListContextType = {
  Leaderboards: Leaderboard[];
  loading: boolean;
  fetchLeaderboards: (params: LeaderboardListParams) => Promise<Leaderboard[]>;
};

export const LeaderboardListContext = createContext({} as LeaderboardListContextType);

export const LeaderboardListProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const [Leaderboards, setLeaderboards] = useState<Leaderboard[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchLeaderboards = async (params: LeaderboardListParams) => {
    setLoading(true);
    let LeaderboardData: Leaderboard[] = [];
    try {
      LeaderboardData = await LeaderboardAPI.fetchLeaderboardList(params);
      setLeaderboards(LeaderboardData);
    } catch (e) {
      console.log(e);
    }
    setLoading(false);
    return LeaderboardData;
  };

  return (
    <LeaderboardListContext.Provider value={{ Leaderboards, loading, fetchLeaderboards }}>
      {children}
    </LeaderboardListContext.Provider>
  );
};