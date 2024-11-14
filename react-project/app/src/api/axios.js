import axios from "axios";

export const authAxios = axios.create({
	baseURL: process.env.REACT_APP_BACKEND_URL,
	headers: {
		"Content-Type": "application/json",
	},
});

export const authAxiosMultipart = axios.create({
	baseURL: process.env.REACT_APP_BACKEND_URL,
	headers: {
		"Content-Type": "multipart/form-data",
	},
});