// @lovable.dev/vite-tanstack-config already includes standard plugins (tailwindcss, tsConfigPaths, etc.)
// Additional configuration is passed to vite via defineConfig({ vite: { ... } }).
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

// Export TanStack Start configuration with production sourcemaps enabled
export default defineConfig({
  // Configure underlying Vite build options
  vite: {
    // Build options
    build: {
      // Enable production sourcemaps so client stack traces show real source files and line numbers
      sourcemap: true,
    },
  },
  // Configure TanStack Start server entrypoint
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (SSR error wrapper)
    server: { entry: "server" },
  },
});
