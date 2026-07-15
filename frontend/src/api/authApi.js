import axiosInstance from './axiosInstance'

export const login = async (username, password) => {
  const res = await axiosInstance.post('/auth/login/', { username, password })
  return res.data
}

export const register = async (username, email, password) => {
  const res = await axiosInstance.post('/auth/register/', { username, email, password })
  return res.data
}

export const getMe = async () => {
  const res = await axiosInstance.get('/auth/me/')
  return res.data
}
