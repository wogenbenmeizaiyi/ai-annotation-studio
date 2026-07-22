/* =========================
 * COCO Dataset TypeScript
 * ========================= */

import type { CocoCategory } from './CocoCategory'

/** 通用 JSON 类型 */
export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue }

/* ---------- Info ---------- */
export interface CocoInfo {
  year: number
  version: string
  description: string
  contributor: string
  url: string
  date_created: string
}

/* ---------- License ---------- */
export interface CocoLicense {
  id: number
  name: string
  url?: string
}

/* ---------- Image ---------- */
export interface CocoImage {
  id: number
  file_name: string
  width: number
  height: number

  license?: number
  flickr_url?: string
  coco_url?: string
  date_captured?: string
}

/* ---------- Annotation ---------- */
export type CocoSegmentation = number[][] | number[]

export interface CocoAnnotation {
  id: number
  image_id: number
  category_id: number

  bbox?: number[] // [x, y, w, h]
  segmentation?: CocoSegmentation

  iscrowd: number
  area: number
}

/* ---------- Dataset ---------- */
export interface CocoDataset {
  info: CocoInfo
  licenses: CocoLicense[]
  categories: CocoCategory[]
  images: CocoImage[]
  annotations: CocoAnnotation[]
}

export interface UpdateAnnotationRequest {
  image_id: number
  cocoAnnotations: CocoAnnotation[]
}
