/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The self-hosted fonts live in the repository's design/fonts/ (DESIGN.md
// ## Typography) and are bundled from there. The dev server only serves files
// inside its allow list, so the font directory is added next to the project
// root itself ("." and ".." resolve against this directory).
export default defineConfig({
  plugins: [react()],
  server: {
    fs: {
      allow: [".", "../design/fonts"],
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
