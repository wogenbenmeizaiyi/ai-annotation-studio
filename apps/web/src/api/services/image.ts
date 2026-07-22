import type { ImageItem, ImageUploadResponse, ImageListPage } from '@/types/ImageItem'
import http from '../http'

export const getImage = async (imageId: number): Promise<ImageItem> => {
  return http.get<ImageItem>(`/image/get/${imageId}`)
}

export const uploadImages = async (
  taskName: string,
  files: File[],
): Promise<ImageUploadResponse> => {
  const formData = new FormData()
  formData.append('task_name', taskName)
  files.forEach((file) => formData.append('files', file))

  const res = await http.post<ImageUploadResponse>('/image/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res
}

export const getImageList = async (
  taskName: string,
  options?: { page?: number; page_size?: number },
): Promise<ImageItem[] | ImageListPage> => {
  if (options?.page && options?.page_size) {
    return http.get<ImageListPage>(`/image/list/${taskName}`, {
      params: { page: options.page, page_size: options.page_size },
    })
  }
  return http.get<ImageItem[]>(`/image/list/${taskName}`)
}

export const deleteImage = async (imageId: number): Promise<void> => {
  await http.delete<void>(`/image/delete/${imageId}`)
}
