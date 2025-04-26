# -----------------------------------------------------------------------------
# NearAI – Experimental TypeScript Runner (custom Lambda runtime style)
# Mirrors the structure of aws_runner/ts_runner but swaps in the new
# ts_runner_jutsu code.  No changes to deploy.sh or docker-compose are needed.
# -----------------------------------------------------------------------------

FROM public.ecr.aws/lambda/provided:al2023.2025.01.24.10

# ─────────────────────────────────────────────────────────────────────────────
# 1. OS packages
# ─────────────────────────────────────────────────────────────────────────────
RUN echo -e "[amzn2-core]\n\
name=Amazon Linux 2 Core\n\
mirrorlist=http://amazonlinux.default.amazonaws.com/2/core/latest/x86_64/mirror.list\n\
enabled=1\n\
gpgcheck=0" > /etc/yum.repos.d/amzn2-core.repo

RUN dnf update -y && \
    dnf install -y \
        gcc gcc-c++ make autoconf automake \
        tar gzip openssl openssl-devel \
        bzip2-devel libffi-devel sqlite-devel xz-devel \
        zlib-devel wget ca-certificates && \
    dnf clean all

# ─────────────────────────────────────────────────────────────────────────────
# 2. Node.js 20 LTS
# ─────────────────────────────────────────────────────────────────────────────
RUN curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - && \
    dnf install -y nodejs && \
    echo "Node version: $(node -v)" && \
    echo "NPM  version: $(npm -v)"

# ─────────────────────────────────────────────────────────────────────────────
# 3. Build & install Python 3.11  (provided.* images ship no Python)
# ─────────────────────────────────────────────────────────────────────────────
ENV LDFLAGS="-L/usr/local/lib -L/usr/local/lib64"
ENV CPPFLAGS="-I/usr/local/include -I/usr/local/include/openssl"
ENV PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:/usr/local/lib64/pkgconfig"
ENV LD_LIBRARY_PATH="/usr/local/lib:/usr/local/lib64"

RUN wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz && \
    tar zxvf Python-3.11.9.tgz && \
    cd Python-3.11.9 && \
      ./configure --enable-optimizations \
                  --with-openssl=/usr --with-openssl-rpath=auto \
                  --with-ensurepip=install \
                  LDFLAGS="${LDFLAGS}" CPPFLAGS="${CPPFLAGS}" && \
      make -j$(nproc) && make altinstall && \
    cd .. && rm -rf Python-3.11.9*

# Symlinks for convenience
RUN ln -sf /usr/local/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/local/bin/pip3.11    /usr/bin/pip && \
    python -m pip install --upgrade pip --no-cache-dir

# ─────────────────────────────────────────────────────────────────────────────
# 4. Python requirements selector (same ARG pattern as other runners)
# ─────────────────────────────────────────────────────────────────────────────
ARG FRAMEWORK=""
COPY aws_runner/frameworks/requirements${FRAMEWORK}.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements${FRAMEWORK}.txt

# ─────────────────────────────────────────────────────────────────────────────
# 5. Copy NearAI Python SDK
# ─────────────────────────────────────────────────────────────────────────────
RUN mkdir -p ${LAMBDA_TASK_ROOT}/nearai
COPY nearai ${LAMBDA_TASK_ROOT}/nearai

# ─────────────────────────────────────────────────────────────────────────────
# 6. Copy & build the experimental TS runner
# ─────────────────────────────────────────────────────────────────────────────
COPY ts_runner_jutsu ${LAMBDA_TASK_ROOT}/ts_runner_jutsu
RUN cd ${LAMBDA_TASK_ROOT}/ts_runner_jutsu && \
    npm install && \
    npm config set loglevel=error

# ─────────────────────────────────────────────────────────────────────────────
# 7. Provide Python runtime bootstrap for custom image
# ─────────────────────────────────────────────────────────────────────────────
COPY aws_runner/ts_runner/python_runtime/. ${LAMBDA_RUNTIME_DIR}
RUN pip install --no-cache-dir awslambdaric

# ─────────────────────────────────────────────────────────────────────────────
# 8. Optional build-id for traceability
# ─────────────────────────────────────────────────────────────────────────────
RUN if [ -f aws_runner/build-info.txt ]; then \
      cp aws_runner/build-info.txt ${LAMBDA_TASK_ROOT}/ ; \
    fi

# ─────────────────────────────────────────────────────────────────────────────
# 9. Default command
# ─────────────────────────────────────────────────────────────────────────────
CMD ["nearai/aws_runner/service.handler"]