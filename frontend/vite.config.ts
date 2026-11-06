import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import {appVersion,pwaPlugin} from "./pwa";
const version=appVersion();
export default defineConfig(({ mode }) => ({
  define: {__APP_VERSION__:JSON.stringify(version)},
  plugins: [
    ...(mode!=="pages"?[pwaPlugin(version)]:[]),
    react(),
    ...(mode === "pages"
      ? [
          {
            name: "pages-entry",
            transformIndexHtml: {
              order: "pre" as const,
              handler: (html: string) =>
                html.replace("/src/main.tsx", "/src/pages.tsx").replace(/<link rel="manifest"[^>]*>/g, ""),
            },
          },
        ]
      : []),
  ],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
}));
