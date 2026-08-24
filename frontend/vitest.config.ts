import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/__tests__/**/*.test.ts'],
    setupFiles: ['src/test/setup.ts'],
    env: {
      TZ: 'UTC',
      VITE_OIDC_AUTHORITY: 'http://localhost/dex',
      VITE_OIDC_CLIENT_ID: 'test-client',
      VITE_OIDC_REDIRECT_URI: 'http://localhost/login/callback',
      VITE_OIDC_SILENT_REDIRECT_URI: 'http://localhost/auth/silent-callback',
      VITE_OIDC_POST_LOGOUT_REDIRECT_URI: 'http://localhost/logout',
      VITE_OIDC_SCOPES: 'openid',
    },
  },
})
