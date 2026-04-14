FROM node:22-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy source
COPY . .

# Build
RUN npm run build

# Expose port
EXPOSE 3456

# Start
CMD ["npm", "start"]
