import type { NextConfig } from 'next';

import { env } from './src/env';

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: '/api/near-rpc-proxy', destination: env.NEAR_RPC_URL }];
  },

  webpack(config) {
    // https://react-svgr.com/docs/next/

    // Grab the existing rule that handles SVG imports
    // @ts-expect-error: any types
    const fileLoaderRule = config.module.rules.find((rule) =>
      rule.test?.test?.('.svg'),
    );

    config.module.rules.push(
      // Reapply the existing rule, but only for svg imports ending in ?url
      {
        ...fileLoaderRule,
        test: /\.svg$/i,
        resourceQuery: /url/, // *.svg?url
      },
      // Convert all other *.svg imports to React components
      {
        test: /\.svg$/i,
        issuer: fileLoaderRule.issuer,
        resourceQuery: { not: [...fileLoaderRule.resourceQuery.not, /url/] }, // exclude if *.svg?url
        use: ['@svgr/webpack'],
      },
    );

    // Modify the file loader rule to ignore *.svg, since we have it handled now.
    fileLoaderRule.exclude = /\.svg$/i;

    return config;
  },

  devIndicators: false,
};

export default nextConfig;
