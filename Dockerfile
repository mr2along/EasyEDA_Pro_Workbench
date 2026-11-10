FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:1 \
    SCREEN_WIDTH=1600 \
    SCREEN_HEIGHT=1000 \
    SCREEN_DEPTH=24 \
    APP_HOME=/opt/easyeda-workbench \
    EASYEDA_HOME=/opt/easyeda-pro \
    PROJECTS_DIR=/data/projects \
    PYTHONUNBUFFERED=1

RUN sed -i 's|http://archive.ubuntu.com/ubuntu|https://archive.ubuntu.com/ubuntu|g; s|http://security.ubuntu.com/ubuntu|https://security.ubuntu.com/ubuntu|g' /etc/apt/sources.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    xvfb xfce4 xfce4-terminal dbus-x11 x11-xserver-utils \
    x11vnc novnc websockify nginx supervisor \
    curl wget unzip tar ca-certificates openssl \
    fonts-dejavu-core fonts-liberation \
    libasound2 libatk1.0-0 libatk-bridge2.0-0 libc6 libcairo2 libcups2 \
    libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 libnss3 libx11-xcb1 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libxshmfence1 \
    libxkbcommon0 libxkbcommon-x11-0 libxrender1 libxi6 libxext6 libegl1 libgl1 \
    libxss1 libxtst6 libglib2.0-0 libpango-1.0-0 libpangocairo-1.0-0 \
    libfontconfig1 libfreetype6 libstdc++6 libgcc-s1 libsecret-1-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_HOME}
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY deploy/supervisord.conf /etc/supervisor/conf.d/easyeda.conf
COPY tests ./tests
COPY README.md ./README.md

RUN chmod +x scripts/*.sh && mkdir -p /data/projects /data/automation /opt/easyeda-pro /var/log/supervisor \
    && ln -sf /usr/share/novnc /var/www/novnc

EXPOSE 7860
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD curl -fsS http://127.0.0.1:7860/healthz || exit 1

CMD ["/opt/easyeda-workbench/scripts/entrypoint.sh"]
