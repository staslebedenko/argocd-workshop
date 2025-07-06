# Stage 1: Build stage - inject env vars into HTML/JS  
FROM node:18-alpine AS build  
  
# Set working directory  
WORKDIR /app  
  
# Pass build-time ARG (can be overridden when building the image)  
ARG BACKEND_URL=http://localhost:5000  
  
# Copy your frontend source files  
COPY index.html ./  
  
# Replace placeholder in index.html with actual BACKEND_URL  
RUN sed -i "s|{{BACKEND_URL}}|${BACKEND_URL}|g" index.html  
  
# Stage 2: Serve the files with Nginx  
FROM nginx:alpine  
  
# Copy processed HTML file from build stage  
COPY --from=build /app/index.html /usr/share/nginx/html/index.html