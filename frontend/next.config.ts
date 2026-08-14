import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    scrollRestoration: true,
  },
};

export default nextConfig;