export default {
  clearMocks: true,
  // Have to add this testEnvironmentOptions to avoid an error when running jest
  // https://github.com/mswjs/msw/issues/1786
  testEnvironmentOptions: {
    customExportConditions: [''],
  },
  testEnvironment: "jsdom",
  testMatch: [
    "<rootDir>/kinesinlms_components/**/*.test.ts",
    "<rootDir>/kinesinlms_components/**/*.test.tsx",
  ],
  setupFilesAfterEnv: [
    "<rootDir>/jest-setup.ts",
  ],
  transform: {
    "^.+\\.(ts|tsx)$": "babel-jest",
    "^.+\\.(js|jsx)$": "babel-jest",
  },
  setupFiles: ['./jest.polyfills.js'],
};