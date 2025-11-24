/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },
  env: {
    FASTAPI_URL: process.env.FASTAPI_URL || 'http://localhost:8000',
  },
}

module.exports = nextConfig
