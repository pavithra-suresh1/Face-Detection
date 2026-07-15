import axiosInstance from './axiosInstance'

export const detectFaces = async (imageId, recognize = false) => {
  const res = await axiosInstance.post('/detect/', { image_id: imageId, recognize })
  return res.data
}

export const getFaceDetail = async (faceId) => {
  const res = await axiosInstance.get(`/faces/${faceId}/`)
  return res.data
}

export const recognizeFaces = async (imageId) => {
  const res = await axiosInstance.post('/recognize/', { image_id: imageId })
  return res.data
}

export const verifyFaces = async (imageId1, imageId2) => {
  const res = await axiosInstance.post('/verify/', {
    image_id_1: imageId1,
    image_id_2: imageId2,
  })
  return res.data
}

export const listKnownFaces = async () => {
  const res = await axiosInstance.get('/known-faces/')
  return res.data
}

export const createKnownFace = async (name, email, files) => {
  const formData = new FormData()
  formData.append('name', name)
  formData.append('email', email)
  files.forEach((f) => formData.append('images', f))
  const res = await axiosInstance.post('/known-faces/create/', formData)
  return res.data
}

export const addFaceImages = async (id, files) => {
  const formData = new FormData()
  files.forEach((f) => formData.append('images', f))
  const res = await axiosInstance.post(`/known-faces/${id}/images/`, formData)
  return res.data
}

export const getKnownFace = async (id) => {
  const res = await axiosInstance.get(`/known-faces/${id}/`)
  return res.data
}

export const updateKnownFace = async (id, data) => {
  const res = await axiosInstance.put(`/known-faces/${id}/update/`, data)
  return res.data
}

export const deleteKnownFace = async (id) => {
  const res = await axiosInstance.delete(`/known-faces/${id}/delete/`)
  return res.data
}

export const deleteFaceImage = async (faceId, imageId) => {
  const res = await axiosInstance.delete(`/known-faces/${faceId}/images/${imageId}/`)
  return res.data
}

export const liveDetect = async (file) => {
  const formData = new FormData()
  formData.append('image', file)
  const res = await axiosInstance.post('/detect-live/', formData, {
    timeout: 30000,
  })
  return res.data
}

export const checkHealth = async () => {
  const res = await axiosInstance.get('/health/')
  return res.data
}

export const getHistory = async (page = 1) => {
  const res = await axiosInstance.get(`/history/?page=${page}`)
  return res.data
}

export const getStats = async () => {
  const res = await axiosInstance.get('/stats/')
  return res.data
}

export const updateRecognitionLog = async (id, data) => {
  const res = await axiosInstance.put(`/history/${id}/update/`, data)
  return res.data
}

export const deleteRecognitionLog = async (id) => {
  const res = await axiosInstance.delete(`/history/${id}/delete/`)
  return res.data
}

export const liveCapture = async (file) => {
  const formData = new FormData()
  formData.append('image', file)
  const res = await axiosInstance.post('/capture/', formData, {
    timeout: 30000,
  })
  return res.data
}


