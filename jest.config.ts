export default {
  clearMocks: true,
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
};