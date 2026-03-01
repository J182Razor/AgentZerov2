###############################################################################
# Agent Zero — Self-contained Dockerfile
# Builds entirely from local source. No dependency on agent0ai/* images.
###############################################################################
FROM kalilinux/kali-rolling

ARG BRANCH=local
ENV BRANCH=$BRANCH
ENV LANG=en_US.UTF-8 LANGUAGE=en_US:en LC_ALL=en_US.UTF-8 TZ=UTC
ENV PYENV_ROOT=/opt/pyenv
ENV PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH"

# ── 1. Locale & timezone ────────────────────────────────────────────────────
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y locales tzdata \
    && sed -i -e 's/# \(en_US\.UTF-8 .*\)/\1/' /etc/locale.gen \
    && dpkg-reconfigure --frontend=noninteractive locales \
    && update-locale LANG=en_US.UTF-8 LANGUAGE=en_US:en LC_ALL=en_US.UTF-8 \
    && ln -sf /usr/share/zoneinfo/UTC /etc/localtime \
    && echo "UTC" > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata

# ── 2. System packages + build dependencies (single layer) ─────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        sudo curl wget git cron \
        openssh-server ffmpeg supervisor \
        nodejs npm \
        tesseract-ocr tesseract-ocr-script-latn poppler-utils \
        python3.13 python3.13-venv \
        make build-essential gcc g++ libssl-dev zlib1g-dev libbz2-dev \
        libreadline-dev libsqlite3-dev llvm \
        libncursesw5-dev xz-utils tk-dev libxml2-dev \
        libxmlsec1-dev libffi-dev liblzma-dev \
        libxslt-dev

# ── 3. Python 3.13 system venv ─────────────────────────────────────────────
RUN python3.13 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip pipx ipython requests

# ── 4. pyenv + Python 3.12.4 app venv + PyTorch CPU ───────────────────────
RUN git clone https://github.com/pyenv/pyenv.git /opt/pyenv \
    && eval "$(pyenv init --path)" \
    && pyenv install 3.12.4 \
    && /opt/pyenv/versions/3.12.4/bin/python -m venv /opt/venv-a0 \
    && /opt/venv-a0/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv-a0/bin/pip install --no-cache-dir \
        torch==2.4.0 torchvision==0.19.0 \
        --index-url https://download.pytorch.org/whl/cpu \
    && /opt/venv-a0/bin/pip cache purge

# pyenv profile (for interactive shells)
RUN printf 'export PYENV_ROOT="/opt/pyenv"\nexport PATH="$PYENV_ROOT/bin:$PATH"\neval "$(pyenv init --path)"\n' \
    > /etc/profile.d/pyenv.sh && chmod +x /etc/profile.d/pyenv.sh

# Install uv (fast pip replacement)
RUN curl -Ls https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh

# ── 5. SearXNG (private metasearch engine) ─────────────────────────────────
RUN useradd --shell /bin/bash --system --home-dir /usr/local/searxng \
        --comment 'Privacy-respecting metasearch engine' searxng \
    && usermod -aG sudo searxng \
    && mkdir -p /usr/local/searxng && chown -R searxng:searxng /usr/local/searxng

RUN su - searxng -c '\
    git clone https://github.com/searxng/searxng /usr/local/searxng/searxng-src \
    && python3.13 -m venv /usr/local/searxng/searx-pyenv \
    && echo ". /usr/local/searxng/searx-pyenv/bin/activate" >> /usr/local/searxng/.profile \
    && . /usr/local/searxng/searx-pyenv/bin/activate \
    && pip install --no-cache-dir -U pip setuptools wheel pyyaml lxml msgspec typing_extensions \
    && cd /usr/local/searxng/searxng-src \
    && pip install --no-cache-dir --use-pep517 --no-build-isolation . \
    && pip cache purge'

# ── 6. SSH ─────────────────────────────────────────────────────────────────
RUN mkdir -p /var/run/sshd \
    && sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# ── 7. Copy runtime filesystem overlay + app source ───────────────────────
COPY ./docker/run/fs/ /
COPY ./ /git/agent-zero

# ── 8. Install Agent Zero into venv ───────────────────────────────────────
RUN bash /ins/pre_install.sh $BRANCH
RUN bash /ins/install_A0.sh $BRANCH

# Playwright + Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-unifont libnss3 libnspr4 libatk1.0-0 libatspi2.0-0 \
        libxcomposite1 libxdamage1 libatk-bridge2.0-0 libcups2 \
    && . /opt/venv-a0/bin/activate \
    && uv pip install playwright \
    && PLAYWRIGHT_BROWSERS_PATH=/a0/tmp/playwright playwright install chromium --only-shell

# ── 9. Cleanup ────────────────────────────────────────────────────────────
RUN rm -rf /var/lib/apt/lists/* && apt-get clean \
    && . /opt/venv-a0/bin/activate && pip cache purge && uv cache prune

# ── 10. Expose & run ─────────────────────────────────────────────────────
EXPOSE 22 80

RUN chmod +x /exe/initialize.sh /exe/run_A0.sh /exe/run_searxng.sh /exe/run_tunnel_api.sh

CMD ["/exe/initialize.sh", "local"]
