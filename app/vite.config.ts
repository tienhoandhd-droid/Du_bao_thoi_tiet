import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// Pages phục vụ ở đường dẫn /Du_bao_thoi_tiet/ → base BẮT BUỘC khớp tên repo,
// nếu không asset (JS/CSS) sẽ 404 khi deploy.
export default defineConfig({
  base: "/Du_bao_thoi_tiet/",
  plugins: [react()],
  resolve: {
    alias: {
      // alias '@' trỏ vào src (chuẩn shadcn) — dùng ESM, tránh __dirname
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
