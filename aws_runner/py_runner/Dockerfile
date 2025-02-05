FROM public.ecr.aws/lambda/python:3.11

RUN yum install -y gcc libffi-devel openssl-devel shadow-utils acl tar gzip curl

# pass with --build-arg FRAMEWORK=-langgraph
ARG FRAMEWORK=""

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

# Save Build Id
RUN if [ -f aws_runner/build-info.txt ]; then \
        cp aws_runner/build-info.txt ${LAMBDA_TASK_ROOT}/; \
    else \
        # remove old Build Id if new build-info.txt is not present
        rm -f ${LAMBDA_TASK_ROOT}/build-info.txt; \
    fi

CMD [ "nearai/aws_runner/service.handler" ]

