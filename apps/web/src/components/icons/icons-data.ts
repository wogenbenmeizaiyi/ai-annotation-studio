/* AI Studio 自绘图标集 — Paper + Ink + Cinnabar 设计语言
 * 全部 viewBox 0 0 24 24, 默认 1.5px 描边, stroke=currentColor.
 * 通过 Icon.vue 组件渲染: <Icon name="folder" :size="19" />
 */

export type IconShape =
  | { t: 'p'; d: string; fill?: boolean }
  | { t: 'c'; cx: number; cy: number; r: number; fill?: boolean }
  | { t: 'r'; x: number; y: number; w: number; h: number; fill?: boolean }
  | { t: 'l'; x1: number; y1: number; x2: number; y2: number }

export const icons: Record<string, IconShape[]> = {
  /* ============== 通用 UI ============== */
  menu: [{ t: 'p', d: 'M4 6h16 M4 12h16 M4 18h16' }],
  close: [{ t: 'p', d: 'M6 6l12 12 M18 6L6 18' }],
  'chevron-left': [{ t: 'p', d: 'M14 6l-6 6 6 6' }],
  'chevron-right': [{ t: 'p', d: 'M10 6l6 6-6 6' }],
  'chevron-down': [{ t: 'p', d: 'M6 10l6 6 6-6' }],
  'chevron-up': [{ t: 'p', d: 'M6 14l6-6 6 6' }],
  'arrow-up': [
    { t: 'p', d: 'M12 19V5 M5 12l7-7 7 7' },
  ],
  'arrow-down': [
    { t: 'p', d: 'M12 5v14 M19 12l-7 7-7-7' },
  ],
  'arrow-right': [
    { t: 'p', d: 'M4 12h16 M14 6l6 6-6 6' },
  ],
  'arrow-left': [
    { t: 'p', d: 'M20 12H4 M10 18l-6-6 6-6' },
  ],
  plus: [{ t: 'p', d: 'M12 5v14 M5 12h14' }],
  minus: [{ t: 'p', d: 'M5 12h14' }],
  check: [{ t: 'p', d: 'M5 12l5 5L20 7' }],

  /* ============== 状态 / 提示 ============== */
  info: [
    { t: 'c', cx: 12, cy: 12, r: 9 },
    { t: 'p', d: 'M12 11v5 M12 7.5v.5' },
  ],
  alert: [
    { t: 'p', d: 'M12 3l9 16H3z' },
    { t: 'p', d: 'M12 10v5 M12 16.5v.5' },
  ],
  help: [
    { t: 'c', cx: 12, cy: 12, r: 9 },
    { t: 'p', d: 'M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.8.4-1 .9-1 1.7 M12 16.5v.5' },
  ],
  'check-circle': [
    { t: 'c', cx: 12, cy: 12, r: 9 },
    { t: 'p', d: 'M8 12l3 3 5-6' },
  ],
  'check-circle-outline': [
    { t: 'c', cx: 12, cy: 12, r: 9 },
    { t: 'p', d: 'M8 12l3 3 5-6' },
  ],
  'alert-circle': [
    { t: 'c', cx: 12, cy: 12, r: 9 },
    { t: 'p', d: 'M12 8v5 M12 15.5v.5' },
  ],
  'alert-circle-outline': [
    { t: 'c', cx: 12, cy: 12, r: 9 },
    { t: 'p', d: 'M12 8v5 M12 15.5v.5' },
  ],

  /* ============== 操作 ============== */
  refresh: [
    { t: 'p', d: 'M4 12a8 8 0 0 1 14-5.3L20 5v5h-5l2-2A6 6 0 1 0 18 12' },
  ],
  restart: [
    { t: 'p', d: 'M4 12a8 8 0 1 0 2.3-5.7 M4 4v4h4' },
  ],
  delete: [
    { t: 'p', d: 'M4 7h16 M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2 M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13 M10 11v6 M14 11v6' },
  ],
  'delete-outline': [
    { t: 'p', d: 'M4 7h16 M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2 M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13' },
    { t: 'p', d: 'M10 11v6 M14 11v6' },
  ],
  download: [
    { t: 'p', d: 'M12 4v12 M7 11l5 5 5-5 M4 20h16' },
  ],
  upload: [
    { t: 'p', d: 'M12 20V8 M7 13l5-5 5 5 M4 4h16' },
  ],
  'upload-outline': [
    { t: 'p', d: 'M12 20V8 M7 13l5-5 5 5' },
    { t: 'p', d: 'M4 4h16' },
  ],
  copy: [
    { t: 'r', x: 8, y: 8, w: 12, h: 12 },
    { t: 'p', d: 'M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3' },
  ],
  lock: [
    { t: 'r', x: 5, y: 11, w: 14, h: 10 },
    { t: 'p', d: 'M8 11V7a4 4 0 0 1 8 0v4' },
  ],
  logout: [
    { t: 'p', d: 'M14 4h5a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-5 M10 8l-4 4 4 4 M6 12h12' },
  ],
  play: [{ t: 'p', d: 'M7 5l12 7-12 7z', fill: true }],
  'play-circle': [
    { t: 'c', cx: 12, cy: 12, r: 9 },
    { t: 'p', d: 'M10 8l6 4-6 4z', fill: true },
  ],
  pencil: [
    { t: 'p', d: 'M4 20l4-1 11-11-3-3L5 16l-1 4z M14 5l3 3' },
  ],
  drag: [
    { t: 'c', cx: 9, cy: 6, r: 1, fill: true },
    { t: 'c', cx: 15, cy: 6, r: 1, fill: true },
    { t: 'c', cx: 9, cy: 12, r: 1, fill: true },
    { t: 'c', cx: 15, cy: 12, r: 1, fill: true },
    { t: 'c', cx: 9, cy: 18, r: 1, fill: true },
    { t: 'c', cx: 15, cy: 18, r: 1, fill: true },
  ],
  home: [
    { t: 'p', d: 'M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1v-9z' },
  ],
  circle: [{ t: 'c', cx: 12, cy: 12, r: 3, fill: true }],

  /* ============== 领域 — 标注 ============== */
  folder: [
    { t: 'p', d: 'M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6z' },
  ],
  'folder-open': [
    { t: 'p', d: 'M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v1H3V6z' },
    { t: 'p', d: 'M3 9h18l-2 9a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1L3 9z' },
  ],
  clipboard: [
    { t: 'r', x: 6, y: 4, w: 12, h: 17 },
    { t: 'p', d: 'M9 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1' },
    { t: 'p', d: 'M9 11h6 M9 15h6 M9 19h4' },
  ],
  'clipboard-text': [
    { t: 'r', x: 6, y: 4, w: 12, h: 17 },
    { t: 'p', d: 'M9 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1' },
    { t: 'p', d: 'M9 11h6 M9 15h6 M9 19h4' },
  ],
  image: [
    { t: 'r', x: 3, y: 4, w: 18, h: 16 },
    { t: 'c', cx: 9, cy: 10, r: 1.5 },
    { t: 'p', d: 'M3 17l5-5 5 5 3-3 5 5' },
  ],
  'image-outline': [
    { t: 'r', x: 3, y: 4, w: 18, h: 16 },
    { t: 'c', cx: 9, cy: 10, r: 1.5 },
    { t: 'p', d: 'M3 17l5-5 5 5 3-3 5 5' },
  ],
  'image-multiple': [
    { t: 'r', x: 3, y: 4, w: 13, h: 13 },
    { t: 'r', x: 6, y: 7, w: 15, h: 14 },
    { t: 'p', d: 'M9 17l3-3 3 3 3-3 3 3' },
  ],
  'file-image': [
    { t: 'p', d: 'M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z' },
    { t: 'p', d: 'M14 3v5h5' },
    { t: 'c', cx: 10, cy: 14, r: 1.5 },
    { t: 'p', d: 'M7 19l3-3 3 3 2-2 2 2' },
  ],
  target: [
    { t: 'c', cx: 12, cy: 12, r: 9 },
    { t: 'c', cx: 12, cy: 12, r: 5 },
    { t: 'c', cx: 12, cy: 12, r: 1.5, fill: true },
    { t: 'l', x1: 12, y1: 2, x2: 12, y2: 4 },
    { t: 'l', x1: 12, y1: 20, x2: 12, y2: 22 },
    { t: 'l', x1: 2, y1: 12, x2: 4, y2: 12 },
    { t: 'l', x1: 20, y1: 12, x2: 22, y2: 12 },
  ],
  radar: [
    { t: 'c', cx: 12, cy: 12, r: 9 },
    { t: 'c', cx: 12, cy: 12, r: 5 },
    { t: 'p', d: 'M12 12L4 8 M12 12l5 7' },
    { t: 'c', cx: 12, cy: 12, r: 1.2, fill: true },
  ],

  /* ============== 领域 — AI / 模型 ============== */
  cube: [
    { t: 'p', d: 'M12 3l8 4v10l-8 4-8-4V7l8-4z' },
    { t: 'p', d: 'M4 7l8 4 8-4 M12 11v10' },
  ],
  'vector-combine': [
    { t: 'r', x: 3, y: 3, w: 9, h: 9 },
    { t: 'r', x: 12, y: 12, w: 9, h: 9 },
    { t: 'p', d: 'M7.5 12h9 M12 7.5v9' },
  ],
  brain: [
    { t: 'p', d: 'M9 4a3 3 0 0 0-3 3v1a3 3 0 0 0-2 2.8V12a3 3 0 0 0 2 2.8V16a3 3 0 0 0 3 3 3 3 0 0 0 3-3V4a3 3 0 0 0-3 0z' },
    { t: 'p', d: 'M15 4a3 3 0 0 1 3 3v1a3 3 0 0 1 2 2.8V12a3 3 0 0 1-2 2.8V16a3 3 0 0 1-3 3 3 3 0 0 1-3-3' },
  ],
  'auto-fix': [
    { t: 'p', d: 'M3 21l12-12 M14 4l2 2 M19 3l1 2 2 1-2 1-1 2-1-2-2-1 2-1z' },
  ],
  wand: [
    { t: 'p', d: 'M3 21l12-12 M14 4l2 2 M19 3l1 2 2 1-2 1-1 2-1-2-2-1 2-1z' },
  ],
  harddisk: [
    { t: 'p', d: 'M4 5a8 3 0 0 1 16 0v14a8 3 0 0 1-16 0V5z' },
    { t: 'p', d: 'M4 12a8 3 0 0 0 16 0' },
  ],
  layers: [
    { t: 'p', d: 'M12 3l9 5-9 5-9-5 9-5z' },
    { t: 'p', d: 'M3 13l9 5 9-5 M3 17l9 5 9-5' },
  ],
  'chart-box': [
    { t: 'r', x: 3, y: 3, w: 18, h: 18 },
    { t: 'p', d: 'M7 16v-3 M12 16V8 M17 16v-5' },
  ],
  'chart-box-outline': [
    { t: 'r', x: 3, y: 3, w: 18, h: 18 },
    { t: 'p', d: 'M7 16v-3 M12 16V8 M17 16v-5' },
  ],
  tune: [
    { t: 'p', d: 'M4 7h10 M18 7h2 M14 5v4 M4 12h2 M10 12h10 M8 10v4 M4 17h12 M20 17h0 M18 15v4' },
  ],
  bulb: [
    { t: 'p', d: 'M9 18h6 M10 21h4' },
    { t: 'p', d: 'M12 3a6 6 0 0 1 4 10.5c-.5.4-1 .9-1 1.5v1H9v-1c0-.6-.5-1.1-1-1.5A6 6 0 0 1 12 3z' },
  ],
  'lightbulb-on': [
    { t: 'p', d: 'M9 18h6 M10 21h4' },
    { t: 'p', d: 'M12 3a6 6 0 0 1 4 10.5c-.5.4-1 .9-1 1.5v1H9v-1c0-.6-.5-1.1-1-1.5A6 6 0 0 1 12 3z' },
    { t: 'l', x1: 12, y1: 2, x2: 12, y2: 4 },
    { t: 'l', x1: 4, y1: 12, x2: 6, y2: 12 },
    { t: 'l', x1: 18, y1: 12, x2: 20, y2: 12 },
    { t: 'l', x1: 6, y1: 6, x2: 7.5, y2: 7.5 },
    { t: 'l', x1: 16.5, y1: 16.5, x2: 18, y2: 18 },
  ],
  cog: [
    { t: 'c', cx: 12, cy: 12, r: 3 },
    { t: 'p', d: 'M12 1v3 M12 20v3 M4.2 4.2l2.1 2.1 M17.7 17.7l2.1 2.1 M1 12h3 M20 12h3 M4.2 19.8l2.1-2.1 M17.7 6.3l2.1-2.1' },
  ],
  document: [
    { t: 'p', d: 'M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z' },
    { t: 'p', d: 'M14 3v5h5' },
    { t: 'p', d: 'M9 13h6 M9 17h6' },
  ],
  'file-document': [
    { t: 'p', d: 'M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z' },
    { t: 'p', d: 'M14 3v5h5' },
    { t: 'p', d: 'M9 13h6 M9 17h6' },
  ],
  cloud: [
    { t: 'p', d: 'M7 18a4 4 0 0 1-1-7.9 5 5 0 0 1 9.8-1A4 4 0 0 1 17 18H7z' },
  ],
  'cloud-upload': [
    { t: 'p', d: 'M7 18a4 4 0 0 1-1-7.9 5 5 0 0 1 9.8-1A4 4 0 0 1 17 18H7z' },
    { t: 'p', d: 'M12 11v8 M9 14l3-3 3 3' },
  ],
  'cloud-upload-outline': [
    { t: 'p', d: 'M7 18a4 4 0 0 1-1-7.9 5 5 0 0 1 9.8-1A4 4 0 0 1 17 18H7z' },
    { t: 'p', d: 'M12 11v8 M9 14l3-3 3 3' },
  ],
  'file-upload': [
    { t: 'p', d: 'M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z' },
    { t: 'p', d: 'M14 3v5h5' },
    { t: 'p', d: 'M12 11v7 M9 14l3-3 3 3' },
  ],

  /* ============== 领域 — 用户 / 系统 ============== */
  users: [
    { t: 'c', cx: 9, cy: 8, r: 3 },
    { t: 'p', d: 'M3 20a6 6 0 0 1 12 0' },
    { t: 'c', cx: 17, cy: 9, r: 2.5 },
    { t: 'p', d: 'M14 20a4.5 4.5 0 0 1 7-3.7' },
  ],
  'account-group': [
    { t: 'c', cx: 9, cy: 8, r: 3 },
    { t: 'p', d: 'M3 20a6 6 0 0 1 12 0' },
    { t: 'c', cx: 17, cy: 9, r: 2.5 },
    { t: 'p', d: 'M14 20a4.5 4.5 0 0 1 7-3.7' },
  ],
  account: [
    { t: 'c', cx: 12, cy: 8, r: 4 },
    { t: 'p', d: 'M4 20a8 8 0 0 1 16 0' },
  ],
  shield: [
    { t: 'p', d: 'M12 2l8 4v6c0 5-3.5 9-8 10-4.5-1-8-5-8-10V6l8-4z' },
    { t: 'p', d: 'M12 8l1.2 2.5 2.6.4-1.9 1.8.5 2.6L12 14l-2.4 1.3.5-2.6-1.9-1.8 2.6-.4z', fill: true },
  ],
  'shield-crown': [
    { t: 'p', d: 'M3 6l3 12h12l3-12-5 4-4-6-4 6-5-4z' },
    { t: 'p', d: 'M5 18h14' },
  ],
  clock: [
    { t: 'c', cx: 12, cy: 12, r: 9 },
    { t: 'p', d: 'M12 7v5l3 2' },
  ],
  'clock-outline': [
    { t: 'c', cx: 12, cy: 12, r: 9 },
    { t: 'p', d: 'M12 7v5l3 2' },
  ],
  'clock-check': [
    { t: 'c', cx: 12, cy: 12, r: 9 },
    { t: 'p', d: 'M12 7v5l3 2' },
    { t: 'p', d: 'M8 17l2 2 4-4' },
  ],
  calendar: [
    { t: 'r', x: 3, y: 5, w: 18, h: 16 },
    { t: 'p', d: 'M3 10h18 M8 3v4 M16 3v4' },
  ],
  'calendar-blank': [
    { t: 'r', x: 3, y: 5, w: 18, h: 16 },
    { t: 'p', d: 'M3 10h18 M8 3v4 M16 3v4' },
  ],
  radar2: [
    { t: 'c', cx: 12, cy: 12, r: 9 },
    { t: 'c', cx: 12, cy: 12, r: 5 },
    { t: 'p', d: 'M12 12L4 8 M12 12l5 7' },
    { t: 'c', cx: 12, cy: 12, r: 1.2, fill: true },
  ],
}

/* 所有可用图标名 — 给 IDE 自动补全用 */
export type IconName = keyof typeof icons
