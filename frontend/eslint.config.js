import js from '@eslint/js';
import pluginVue from 'eslint-plugin-vue';

export default [
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        // Browser + Vite globals used in the app.
        window: 'readonly',
        document: 'readonly',
        navigator: 'readonly',
        localStorage: 'readonly',
        console: 'readonly',
        setTimeout: 'readonly',
        TextDecoder: 'readonly',
        atob: 'readonly',
      },
    },
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },
  {
    // EmailDetail renders email HTML via v-html, but only after DOMPurify
    // sanitization (see src/components/EmailDetail.vue `sanitizedHtml`).
    files: ['src/components/EmailDetail.vue'],
    rules: {
      'vue/no-v-html': 'off',
    },
  },
  {
    // Node-context config files.
    files: ['vite.config.js', 'eslint.config.js', 'postcss.config.js', 'tailwind.config.js'],
    languageOptions: {
      globals: { process: 'readonly' },
    },
  },
  {
    ignores: ['dist/**', 'node_modules/**'],
  },
];
