// import { Post, PostListParams, SubmitPost } from "../types/post";
import { authAxios, authAxiosMultipart } from "./axios";

export class PostAPI {
//   static async fetchPostList(params: PostListParams): Promise<Post[]> {
//     const response = await authAxios.get("posts/", {
//       params: params,
//       paramsSerializer: { indexes: null },
//       headers: sessionStorage.getItem("token")
//         ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
//         : {},
//     });
//     // 画像の配列を画像の URL の配列に変換
//     response.data = response.data.map((post: any) => {
//       post.images = post.images.map((obj: any) => obj.image);
//       return post;
//     });
//     return response.data;
//   }

//   static async fetchPostDetail(id: number): Promise<Post> {
//     const response = await authAxios.get(`posts/${id}/`, {
//       headers: sessionStorage.getItem("token")
//         ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
//         : {},
//     });
//     // 画像の配列を画像の URL の配列に変換
//     response.data.images = response.data.images.map((obj: any) => obj.image);
//     return response.data;
//   }

//   static async createPost(data: SubmitPost): Promise<Post> {
//     const response = await authAxiosMultipart.post(`posts/`, data, {
//       headers: sessionStorage.getItem("token")
//         ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
//         : {},
//     });
//     return response.data;
//   }

//   static async deletePost(id: number): Promise<void> {
//     await authAxios.delete(`posts/${id}/`, {
//       headers: sessionStorage.getItem("token")
//         ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
//         : {},
//     });
//   }

//   static async like(id: number): Promise<void> {
//     await authAxios.post(
//       `posts/${id}/like/`,
//       {},
//       {
//         headers: sessionStorage.getItem("token")
//           ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
//           : {},
//       }
//     ).catch(() => { });
//   }

//   static async unlike(id: number): Promise<void> {
//     await authAxios.post(
//       `posts/${id}/unlike/`,
//       {},
//       {
//         headers: sessionStorage.getItem("token")
//           ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
//           : {},
//       }
//     ).catch(() => { });
//   }

//   static async fetchTagRecommend(data: SubmitPost): Promise<string[]> {
//     const response = await authAxiosMultipart.post("posts/tag_recommend/", data, {
//       headers: sessionStorage.getItem("token")
//         ? { Authorization: `Token ${sessionStorage.getItem("token")}` }
//         : {},
//     });
//     console.log(response.data);
//     return response.data.recommend_tags ?? [];
//   }
}