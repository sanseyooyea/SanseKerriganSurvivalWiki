FROM docker.1ms.run/library/node:22 AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --registry=https://registry.npmmirror.com
COPY . .
RUN npm run build

FROM docker.1ms.run/library/node:22-slim AS runner

WORKDIR /app
COPY --from=builder /app/.output ./.output
COPY --from=builder /app/data ./data

ENV HOST=0.0.0.0
ENV PORT=3000
ENV NODE_ENV=production

EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
