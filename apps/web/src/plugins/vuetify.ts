import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import { zhHans } from 'vuetify/locale'

export default createVuetify({
  locale: {
    locale: 'zhHans',
    fallback: 'zhHans',
    messages: { zhHans },
  },
  icons: {
    defaultSet: 'mdi',
  },
  theme: {
    defaultTheme: 'linearDark',
    themes: {
      linearDark: {
        dark: true,
        colors: {
          background: '#010102',
          surface: '#0f1011',
          'surface-bright': '#191a1b',
          'surface-light': '#18191a',
          'surface-variant': '#141516',
          'on-background': '#f7f8f8',
          'on-surface': '#f7f8f8',
          'on-surface-variant': '#d0d6e0',
          primary: '#5e6ad2',
          'on-primary': '#ffffff',
          secondary: '#7a7fad',
          'on-secondary': '#ffffff',
          success: '#27a644',
          warning: '#d6a756',
          error: '#e5484d',
          info: '#6e7fe8',
        },
        variables: {
          'border-color': '#34343a',
          'border-opacity': 0.72,
          'high-emphasis-opacity': 0.96,
          'medium-emphasis-opacity': 0.68,
          'disabled-opacity': 0.42,
          'hover-opacity': 0.06,
          'focus-opacity': 0.12,
          'selected-opacity': 0.12,
        },
      },
    },
  },
  defaults: {
    VBtn: {
      elevation: 0,
      rounded: 'md',
    },
    VCard: {
      elevation: 0,
      rounded: 'lg',
    },
    VChip: {
      rounded: 'sm',
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
  },
})
