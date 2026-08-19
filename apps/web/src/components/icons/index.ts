/* AI Studio 图标集入口
 * 重新导出 Icon 组件 + 类型, 业务代码统一从这里 import
 *   import { Icon } from '@/components/icons'
 *   <Icon name="folder" :size="19" />
 */
export { default as Icon } from './Icon.vue'
export type { IconName, IconShape } from './icons-data'
export { icons } from './icons-data'
