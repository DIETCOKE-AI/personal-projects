import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  base: "./",
  plugins: [vue()],
  server: {
    cors: true, // 允许跨域
    proxy: {
      // 代理1：指向中药识别大模型后端 (保留)
      '/flask': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        ws: true,
        rewrite: path => path.replace(/^\/flask/, '')
      },
      // 代理2：指向若依用户管理后端 (新增)
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api/, '')
      }
    }
  },
  build: {
    outDir: "dist",
    rollupOptions: {
      input: {
        renderer: path.resolve(__dirname, "index.html"),
        main: path.resolve(__dirname, "src/main/index.js"),
        preload: path.resolve(__dirname, "src/preload/preload.js"), // <--- 新增 preload 入口
      },
      output: {
        entryFileNames: (chunkInfo) => {
          if (chunkInfo.name === 'main') return 'main/index.js';
          if (chunkInfo.name === 'preload') return 'preload/preload.js'; // <--- 新增 preload 的输出规则
          return 'renderer/assets/[name]-[hash].js';
        },
        chunkFileNames: 'renderer/assets/[name]-[hash].js',
        assetFileNames: 'renderer/assets/[name]-[hash].[ext]',
      },
      external: ['electron', 'path', 'fs', 'child_process', 'url']
    }
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
});