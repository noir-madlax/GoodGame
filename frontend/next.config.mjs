/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  typedRoutes: false,
  eslint: {
    // Temporarily ignore ESLint errors during build to allow migration.
    ignoreDuringBuilds: true,
  },
}

export default nextConfig


