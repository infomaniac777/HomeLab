FROM node:18-alpine

# Set timezone
ENV TZ=Asia/Kolkata

# Install tzdata, set timezone, then remove tzdata
RUN apk add --no-cache tzdata && \
    cp /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apk del tzdata

WORKDIR /app

# Copy package file
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY server.js .

# Expose WebSocket and metrics port
EXPOSE 3100

# Start the server
CMD ["node", "server.js"]