import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";
import sitemapPlugin from "./vite-plugin-sitemap";
import indexNowPlugin from "./vite-plugin-indexnow";

const DOCUSAURUS_DEV_URL = "http://localhost:3000";

function docusaurusRedirect(): Plugin {
  return {
    name: "docusaurus-redirect",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url?.startsWith("/docs") || req.url?.startsWith("/blog")) {
          res.writeHead(302, { Location: `${DOCUSAURUS_DEV_URL}${req.url}` });
          res.end();
          return;
        }
        next();
      });
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
  },
  plugins: [
    react(),
    mode === "development" && componentTagger(),
    mode === "development" && docusaurusRedirect(),
    sitemapPlugin(),
    indexNowPlugin(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    target: "es2020",
    cssMinify: true,
    chunkSizeWarningLimit: 800,
    // Filter out heavy chunks that are only reachable via lazy imports on
    // routes other than "/" (e.g. the markdown bundle is /shared-only).
    modulePreload: {
      polyfill: false,
      resolveDependencies(_filename, deps) {
        return deps.filter(
          (d) =>
            !d.includes("markdown-") &&
            !d.includes("Shared-") &&
            !d.includes("polar-") &&
            !d.includes("charts-") &&
            !d.includes("datepicker-") &&
            !d.includes("carousel-"),
        );
      },
    },
    rollupOptions: {
      output: {
        // Split only feature-specific deps into their own chunks. Anything that
        // chains back through react/react-dom stays in the default vendor chunk
        // so we don't create import cycles.
        manualChunks: (id) => {
          if (!id.includes("node_modules")) return undefined;
          if (id.includes("react-markdown") || id.includes("remark-") || id.includes("micromark") || id.includes("mdast-") || id.includes("hast-") || id.includes("unist-") || id.includes("unified")) return "markdown";
          if (id.includes("recharts") || id.includes("d3-")) return "charts";
          if (id.includes("react-day-picker") || id.includes("date-fns")) return "datepicker";
          if (id.includes("@polar-sh")) return "polar";
          if (id.includes("embla-carousel")) return "carousel";
          return undefined;
        },
      },
    },
  },
}));
