import type { NextConfig } from "next";

// The UI is a pure consumer of the Python execution API (poc/inspector_api.py).
// Everything under /api is proxied to it, so the browser sees one origin and the
// UI carries no execution logic — and no second copy of any graph.
const API = process.env.INSPECTOR_API ?? "http://127.0.0.1:8123";

const nextConfig: NextConfig = {
  // Dev-only: let the dev server be reached as 127.0.0.1 as well as localhost
  // (Next 16 blocks cross-origin dev resources by default).
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};

export default nextConfig;
