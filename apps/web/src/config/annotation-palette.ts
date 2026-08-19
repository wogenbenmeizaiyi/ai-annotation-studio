/* AI Studio 标注分类调色板 — Paper + Ink + Cinnabar 设计语言
 *
 * 当前业务只允许创建一种类型的标注, 所以全部用主色朱砂 #cf4a36.
 * API 仍然按 id 入参, 方便未来需要多色时改回散列映射.
 */

/** 主色 — 朱砂. 所有标注统一使用此色. */
export const ANNOTATION_COLOR = '#cf4a36'

/** @deprecated 历史别名, 保留只是为了不破坏旧引用; 实际只含主色. */
export const ANNOTATION_PALETTE: string[] = [ANNOTATION_COLOR]

/** @deprecated 历史别名, 保留只是为了不破坏旧引用; 实际只含主色. */
export const ANNOTATION_COLOR_BY_ID: Record<number, string> = {}

/** 始终返回主色朱砂. 接受 id 是为了保留 API 兼容性. */
export function annotationColorForId(_id: number): string {
  return ANNOTATION_COLOR
}
