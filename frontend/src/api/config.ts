/**
 * Set VITE_USE_MOCK_API=true (see frontend/.env.example) to work on the interface without the
 * backend running. By default the app talks to the real API.
 */
export const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API === "true";
