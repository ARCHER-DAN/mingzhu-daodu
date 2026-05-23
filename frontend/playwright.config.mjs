/** @type {import('@playwright/test').PlaywrightTestConfig} */
export default {
  testDir: './tests',
  timeout: 120000, // 2分钟超时（AI回复可能较慢）
  expect: {
    timeout: 15000,
  },
  retries: 1,
  use: {
    baseURL: 'http://127.0.0.1:8080',
    headless: true,
    viewport: { width: 1366, height: 768 },
    actionTimeout: 15000,
    ignoreHTTPSErrors: true,
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...{},
        browserName: 'chromium',
        launchOptions: {
          args: ['--no-sandbox', '--disable-setuid-sandbox'],
        },
      },
    },
  ],
  reporter: [
    ['list'],
    ['json', { outputFile: 'test-results/sprint5_results.json' }],
  ],
};
