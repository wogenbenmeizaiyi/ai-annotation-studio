import type { CocoDataset, UpdateAnnotationRequest } from '@/types/CocoDataset'
import http from '../http'

export const getAnnotation = async (imageId: number): Promise<CocoDataset> => {
  try {
    const res = await http.get<CocoDataset>('/annotation/get_by_image', {
      params: {
        image_id: imageId,
      },
    })
    return res
  } catch (error) {
    console.log(error)
    throw error
  }
}

export const updateAnnotation = async (data: UpdateAnnotationRequest) => {
  try {
    await http.post('/annotation/update', data)
  } catch (error) {
    console.error('Failed to update annotation:', error)
    throw error
  }
}
