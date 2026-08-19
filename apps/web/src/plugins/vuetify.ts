import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify, type ThemeDefinition } from 'vuetify'
import { zhHans } from 'vuetify/locale'

/* Paper + Ink + Cinnabar — PassingTrace 主站设计语言 */
const paperInk: ThemeDefinition = {
  dark: false,
  colors: {
    background: '#f5f0e6',  // paper
    surface: '#f5f0e6',     // paper (cards 同色, 用 sand 阴影区分)
    'surface-bright': '#ebe5d9',  // sand
    'surface-light': '#ebe5d9',
    'surface-variant': '#ebe5d9',
    'on-background': '#4a4036',   // ink
    'on-surface': '#4a4036',      // ink
    'on-surface-variant': '#5e6b55',  // sage
    primary: '#cf4a36',      // 朱砂
    'on-primary': '#ffffff',
    'primary-darken-1': '#b03e2c',
    secondary: '#5e6b55',    // sage
    'on-secondary': '#ffffff',
    'secondary-darken-1': '#4a5642',
    success: '#5e6b55',      // sage (status, 不是红)
    'on-success': '#ffffff',
    warning: '#b08a3a',
    'on-warning': '#ffffff',
    error: '#7b2519',        // 深朱砂
    'on-error': '#ffffff',
    info: '#5e6b55',
    'on-info': '#ffffff',
  },
  variables: {
    'border-color': '#4a4036',
    'border-opacity': 0.17,
    'high-emphasis-opacity': 1,
    'medium-emphasis-opacity': 0.66,
    'disabled-opacity': 0.42,
    'hover-opacity': 0.08,
    'focus-opacity': 0.16,
    'selected-opacity': 0.16,
    'theme-on-background': '#4a4036',
    'theme-on-surface': '#4a4036',
  },
}

export default createVuetify({
  locale: {
    locale: 'zhHans',
    fallback: 'zhHans',
    messages: { zhHans },
  },
  /* MDI 字体不再默认加载 — 我们用自绘 SVG 图标;
     保留兜底以防 <v-icon> 还有遗漏, 后续阶段完全清掉 */
  icons: {
    defaultSet: 'mdi',
  },
  theme: {
    defaultTheme: 'paperInk',
    themes: { paperInk },
  },
  defaults: {
    VBtn: {
      elevation: 0,
      rounded: 0,
    },
    VCard: {
      elevation: 0,
      rounded: 0,
    },
    VChip: {
      rounded: 0,
    },
    VTextField: {
      variant: 'outlined',
    },
    VTextarea: {
      variant: 'outlined',
    },
    VSelect: {
      variant: 'outlined',
    },
    VAutocomplete: {
      variant: 'outlined',
    },
    VAlert: {
      variant: 'tonal',
    },
    VDialog: {
      transition: 'fade-transition',
    },
    VSnackbar: {
      rounded: 0,
    },
  },
})
