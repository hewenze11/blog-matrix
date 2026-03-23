FROM node:20-alpine AS base

WORKDIR /app

# Install deps
COPY package.json ./
RUN npm install --legacy-peer-deps

# Build
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_BASE=__API_BASE_PLACEHOLDER__
RUN npm run build

# Production runner
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=base /app/.next/standalone ./
COPY --from=base /app/.next/static ./.next/static
COPY --from=base /app/public ./public 2>/dev/null || true

EXPOSE 3000
CMD ["node", "server.js"]
