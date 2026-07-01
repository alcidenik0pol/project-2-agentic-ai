/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true, // emit out/debug/index.html so GCS dir-index serves /debug/
  images: {
    // Defensive: no next/image usage today, but required for export if added later
    unoptimized: true,
  },
  async rewrites() {
    // Dev-only: ignored under output: 'export'. Proxies /api/* to local backend
    // when a developer has no .env.local.
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8901/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
