/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: [
    "react-markdown",
    "remark-parse",
    "remark-rehype",
    "unified",
    "vfile",
    "mdast-util-to-hast",
    "hast-util-to-jsx-runtime",
    "unist-util-visit",
    "devlop",
  ],
};

export default nextConfig;
