FROM public.ecr.aws/lambda/python:3.11

RUN yum install -y gcc libffi-devel openssl-devel-1:1.0.2k-24.amzn2.0.14 shadow-utils acl && \
    yum clean all && \
    rm -rf /var/cache/yum

# Use Node.js 16+ from EPEL or Amazon Linux Extras (if available)
RUN curl -sL https://rpm.nodesource.com/setup_16.x | bash - \
    && yum install -y nodejs npm \
    && yum clean all \
    && rm -rf /var/cache/yum

# pass with --build-arg FRAMEWORK=-langgraph
ARG FRAMEWORK=""

COPY aws_runner/frameworks/requirements${FRAMEWORK}.txt ${LAMBDA_TASK_ROOT}

RUN pip install --upgrade pip

# Add Datadog Lambda Extension
COPY --from=public.ecr.aws/datadog/lambda-extension:latest /opt/extensions/ /opt/extensions/

RUN pip install datadog-lambda

ENV DD_TRACE_ENABLED=true \
    DD_MERGE_XRAY_TRACES=true \
    DD_LAMBDA_HANDLER="nearai/aws_runner/service.handler" \
    PYTHONPATH="/opt/python:${PYTHONPATH}" \
    DD_ENHANCED_METRICS=true


RUN pip install -r requirements${FRAMEWORK}.txt

# This will build a smaller container, but takes much longer time to run.
# RUN pip install --no-cache-dir -r requirements${FRAMEWORK}.txt && \
#     echo "Package sizes:" && \
#     pip list --format=freeze | while read package; do \
#         package_name=$(echo "$package" | cut -d= -f1); \
#         size=$(du -sh $(pip show "$package_name" | grep Location | cut -d' ' -f2)"/$package_name" 2>/dev/null | cut -f1); \
#         echo "$size $package_name"; \
#     done | sort -hr && \
#     # Cleanup
#     find /usr/local -type d -name __pycache__ -exec rm -rf {} + && \
#     find /usr/local -type f -name '*.pyc' -delete && \
#     find /usr/local -type d -name "tests" -exec rm -rf {} + && \
#     find /usr/local -type d -name "docs" -exec rm -rf {} + && \
#     rm -rf /root/.cache/* /tmp/*

ARG AGENT_RUNNER_USER="agent_runner"
RUN /bin/sh -c "echo Setting agent runner user as $AGENT_RUNNER_USER"

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

# Copy the experimental runner folder
COPY ts_runner_exp ${LAMBDA_TASK_ROOT}/ts_runner_exp

# @NOTE: For supporting experimental ts runner in local environment
# Install the experimental runner code
RUN cd ${LAMBDA_TASK_ROOT}/ts_runner_exp && \
    npm install && \
    npm config set loglevel=error

# Save Build Id
RUN if [ -f aws_runner/build-info.txt ]; then \
        cp aws_runner/build-info.txt ${LAMBDA_TASK_ROOT}/; \
    else \
        # remove old Build Id if new build-info.txt is not present
        rm -f ${LAMBDA_TASK_ROOT}/build-info.txt; \
    fi

# @NOTE: Could not get to work in local dev without commenting out the datadog-lambda
# Invoke the Datadog Lambda Handler that will invoke the main handler
#CMD [ "datadog_lambda.handler.handler" ]
CMD [ "nearai/aws_runner/service.handler" ]