FROM node:20-alpine AS base

FROM base AS runner
WORKDIR /app
ENV NODE_ENV production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy pre-built frontend files
COPY .next/standalone ./
COPY .next/static ./.next/static
COPY public ./public

# Install only production runtime dependencies
COPY package.json package-lock.json* ./
RUN npm ci --only=production --no-audit --no-fund && npm cache clean --force

USER nextjs
EXPOSE 3000
ENV PORT 3000
CMD ["node", "server.js"]
