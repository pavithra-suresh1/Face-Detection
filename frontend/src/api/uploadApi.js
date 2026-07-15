import axiosInstance from './axiosInstance'

export const uploadImage = async (file) => {
  const formData = new FormData()
  formData.append('image', file)
  const res = await axiosInstance.post('/upload/', formData)
  return res.data
}

export const listImages = async (page = 1) => {
  const res = await axiosInstance.get(`/uploads/?page=${page}`)
  return res.data
}

export const getImage = async (id) => {
  const res = await axiosInstance.get(`/uploads/${id}/`)
  return res.data
}

export const deleteImage = async (id) => {
  const res = await axiosInstance.delete(`/uploads/${id}/delete/`)
  return res.data
}
