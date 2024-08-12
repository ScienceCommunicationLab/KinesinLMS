import '@testing-library/jest-dom'

// Do not show console.logs in test output.
global.console = {
  ...console,
  // Uncomment to show a specific log level.
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  // warn: jest.fn(),
  // error: jest.fn(),
};
