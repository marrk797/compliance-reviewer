/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: false,
  },
  // @huggingface/transformers ships an onnxruntime-node fallback that
  // contains .node binaries; we only ever import it from a browser
  // "use client" component, so stub it (and `sharp`, an optional Node-only
  // image dep) out of webpack's resolution. This is the configuration
  // recommended by the Transformers.js Next.js tutorial.
  webpack: (config) => {
    config.resolve = config.resolve || {};
    config.resolve.alias = {
      ...config.resolve.alias,
      "onnxruntime-node$": false,
      sharp$: false,
    };
    return config;
  },
};

export default nextConfig;
