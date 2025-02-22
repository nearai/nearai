FROM public.ecr.aws/lambda/provided:al2023.2025.01.24.10

# Add official Amazon Linux 2 repositories
RUN echo -e "[amzn2-core]\n\
name=Amazon Linux 2 Core\n\
mirrorlist=http://amazonlinux.default.amazonaws.com/2/core/latest/x86_64/mirror.list\n\
enabled=1\n\
gpgcheck=0" > /etc/yum.repos.d/amzn2-core.repo

# install system dependencies
RUN dnf update -y && \
    dnf install -y \
       gcc gcc-c++ make autoconf automake \
       tar gzip openssl openssl-devel bzip2-devel \
       libffi-devel sqlite-devel xz-devel \
       zlib-devel wget ca-certificates \
    && dnf clean all

# install latest nodejs
RUN curl -fsSL https://rpm.nodesource.com/setup_22.x | bash - && \
  dnf install -y nodejs && \
  echo "Node version: $(node -v)" && \
  echo "NPM version: $(npm -v)";

# Set up OpenSSL environment variables
ENV LDFLAGS="-L/usr/local/lib -L/usr/local/lib64"
ENV CPPFLAGS="-I/usr/local/include -I/usr/local/include/openssl"
ENV PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:/usr/local/lib64/pkgconfig"
ENV LD_LIBRARY_PATH="/usr/local/lib:/usr/local/lib64"

# compile python 11 from sources. Python 11 requires by py-near
RUN wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz && \
    tar zxvf Python-3.11.9.tgz && \
    cd Python-3.11.9/ && \
    ./configure \
        --enable-optimizations \
        --with-openssl=/usr \
        --with-openssl-rpath=auto \
        --with-ensurepip=install \
        LDFLAGS="${LDFLAGS}" \
        CPPFLAGS="${CPPFLAGS}" && \
    make -j$(nproc) && \
    make altinstall && \
    cd .. && \
    rm -rf Python-3.11.9*


# Install pip and create symlinks
RUN ln -sf /usr/local/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/local/bin/pip3.11 /usr/bin/pip

RUN python -c "import ssl; print('SSL Module:', ssl.OPENSSL_VERSION)"

RUN python -m pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org

# make sure we have python and pip
RUN python --version && pip --version

# pass with --build-arg FRAMEWORK=-langgraph
ARG FRAMEWORK=""

# install runner python requirements
COPY aws_runner/frameworks/requirements${FRAMEWORK}.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements${FRAMEWORK}.txt

# Copy the Lambda function code for NEAR AI runner
RUN mkdir ${LAMBDA_TASK_ROOT}/nearai
COPY nearai ${LAMBDA_TASK_ROOT}/nearai

# copy ts_agent to temp folder, it will be removed later. This ts_agent is needed to launch agents.
COPY ts_runner/ts_agent /tmp/ts_runner_temp

# build ts_agent (this downloads ts-agent-runner from npm)
RUN mkdir -p ${LAMBDA_TASK_ROOT}/ts_runner && \
cp -r /tmp/ts_runner_temp/* ${LAMBDA_TASK_ROOT}/ts_runner/ && \
mkdir -p ${LAMBDA_TASK_ROOT}/ts_runner/agents && \
cd ${LAMBDA_TASK_ROOT}/ts_runner && \
npm install && npm run build && npm config set loglevel=error

# Clear temp folder
RUN rm -rf /tmp/ts_runner_temp

# Install AWS Lambda python runtime
COPY aws_runner/ts_runner/python_runtime/. ${LAMBDA_RUNTIME_DIR}
RUN pip install awslambdaric

# Save Build Id
RUN if [ -f aws_runner/build-info.txt ]; then \
        cp aws_runner/build-info.txt ${LAMBDA_TASK_ROOT}/; \
    else \
        # remove old Build Id if new build-info.txt is not present
        rm -f ${LAMBDA_TASK_ROOT}/build-info.txt; \
    fi

# Enable AWS service to launch runner
CMD [ "nearai/aws_runner/service.handler" ]

