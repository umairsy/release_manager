import path from "path";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";

export default defineConfig({
  plugins: [
    frappeui({
      frappeProxy: true,
      jinjaBootData: true,
      buildConfig: {
        outDir: "../smoke_console/public/frontend",
        emptyOutDir: true,
        indexHtmlPath: "../smoke_console/www/release/index.html",
      },
    }),
    vue(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  build: {
    target: "es2015",
  },
});
