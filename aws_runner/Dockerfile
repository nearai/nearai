# node image public.ecr.aws/lambda/nodejs:22
FROM public.ecr.aws/lambda/python:3.11

RUN yum install -y gcc libffi-devel openssl-devel shadow-utils acl tar gzip curl

# pass with --build-arg FRAMEWORK=-langgraph
ARG FRAMEWORK=""
ARG TS_RUNNER="False"

RUN if [ "$TS_RUNNER" = "True" ]; then \
    # Only 16.x is supported for a given python image
    curl -fsSL https://rpm.nodesource.com/setup_16.x | bash - && \
    yum install -y nodejs && \
    echo "Node version: $(node -v)" && \
    echo "NPM version: $(npm -v)"; \
fi

COPY aws_runner/frameworks/requirements${FRAMEWORK}.txt ${LAMBDA_TASK_ROOT}

RUN pip install -r requirements${FRAMEWORK}.txt

ARG AGENT_RUNNER_USER="agent_runner"
CMD /bin/sh -c "echo Setting agent runner user as $AGENT_RUNNER_USER"
RUN /usr/sbin/groupadd -r $AGENT_RUNNER_USER && \
    /usr/sbin/useradd -r -g $AGENT_RUNNER_USER -m $AGENT_RUNNER_USER

RUN mkdir -p /$AGENT_RUNNER_USER/.nearai/registry && \
    chown $AGENT_RUNNER_USER:$AGENT_RUNNER_USER /$AGENT_RUNNER_USER/.nearai/registry

RUN chown -R $AGENT_RUNNER_USER:$AGENT_RUNNER_USER /var/task

RUN setfacl -Rdm u:$AGENT_RUNNER_USER:rwx /tmp && \
    setfacl -Rm u:$AGENT_RUNNER_USER:rwx /tmp

# Copy the Lambda function code for NEAR AI runner
RUN mkdir ${LAMBDA_TASK_ROOT}/nearai
COPY nearai ${LAMBDA_TASK_ROOT}/nearai


# copy of ts_runner to temp folder, it will be removed later
COPY nearai/ts_runner /tmp/ts_runner_temp

RUN if [ "$TS_RUNNER" = "True" ]; then \
    mkdir -p ${LAMBDA_TASK_ROOT}/ts_runner && \
    cp -r /tmp/ts_runner_temp/* ${LAMBDA_TASK_ROOT}/ts_runner/ && \
    mkdir -p ${LAMBDA_TASK_ROOT}/ts_runner/agents && \
    cd ${LAMBDA_TASK_ROOT}/ts_runner && \
    npm install && npm run build \
; fi

# Clear temp folder
RUN rm -rf /tmp/ts_runner_temp

# Copy build-info.txt to the image
COPY build-info.txt ${LAMBDA_TASK_ROOT}/
# Read the build ID from the file and save it to the ENV
# ENV BUILD_ID=$(cat /var/task/build-info.txt)
# RUN rm /tmp/build-info.txt

# WORKDIR /
CMD [ "nearai/aws_runner/service.handler" ]

