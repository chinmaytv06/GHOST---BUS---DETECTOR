# Use Node.js base image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files first (better caching)
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy all source code
COPY . .

# Expose React dev server port
EXPOSE 3000

# Run React in development mode (hot reload)
CMD ["npm", "start"]
