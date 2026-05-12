FROM node:20-alpine

WORKDIR /app

ARG VITE_GOOGLE_CLIENT_ID
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY frontend/package.json /app/package.json

RUN npm config set registry https://registry.npmmirror.com && npm install

COPY frontend /app

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
