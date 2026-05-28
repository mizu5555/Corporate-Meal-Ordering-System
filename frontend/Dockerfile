FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker-entrypoint.sh /usr/local/bin/inject-base-path.sh
RUN chmod +x /usr/local/bin/inject-base-path.sh
ENTRYPOINT ["/usr/local/bin/inject-base-path.sh"]
