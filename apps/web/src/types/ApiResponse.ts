// 分页接口类型
export interface ApiResponse<T> {
  success: boolean
  message: string
  data?: T
  code?: number
}

// 示例分页数据类型
export interface ImageNamePage {
  list: string[]
  page: number
  page_size: number
  total: number
}
