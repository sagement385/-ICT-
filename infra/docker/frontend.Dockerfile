FROM node:22-alpine

WORKDIR /workspace/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend ./

