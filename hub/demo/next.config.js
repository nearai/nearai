/* eslint-disable @typescript-eslint/no-unsafe-return */
/* eslint-disable @typescript-eslint/no-unsafe-member-access */
/* eslint-disable @typescript-eslint/no-unsafe-call */
/* eslint-disable @typescript-eslint/no-unsafe-assignment */

import { env } from './src/env.js';

/** @type {import("next").NextConfig} */
const config = {
  experimental: {
    missingSuspenseWithCSRBailout: false,
  },

  async rewrites() {
    return [
      {
        source: '/api/near-rpc-proxy',
        destination: env.NEAR_RPC_URL,
      },
    ];
  },

  webpack(config) {
    // @ts-expect-error https://react-svgr.com/docs/next
    const fileLoaderRule = config.module.rules.find((rule) =>
      rule.test?.test?.('.svg'),
    );
    config.module.rules.push(
      {
        ...fileLoaderRule,
        test: /\.svg$/i,
        resourceQuery: /url/, // *.svg?url
      },
      {
        test: /\.svg$/i,
        issuer: fileLoaderRule.issuer,
        resourceQuery: { not: [...fileLoaderRule.resourceQuery.not, /url/] }, // exclude if *.svg?url
        use: ['@svgr/webpack'],
      },
    );
    fileLoaderRule.exclude = /\.svg$/i;
    return config;
  },
};

export default config;
