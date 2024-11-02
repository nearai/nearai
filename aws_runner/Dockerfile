FROM public.ecr.aws/lambda/python:3.12

# pass with --build-arg FRAMEWORK=-langgraph
ARG FRAMEWORK=""

COPY aws_runner/frameworks/requirements${FRAMEWORK}.txt ${LAMBDA_TASK_ROOT}

RUN pip install -r requirements${FRAMEWORK}.txt

RUN mkdir ${LAMBDA_TASK_ROOT}/aws_runner
RUN mkdir ${LAMBDA_TASK_ROOT}/nearai
COPY aws_runner/service.py ${LAMBDA_TASK_ROOT}/aws_runner/
COPY nearai/agents ${LAMBDA_TASK_ROOT}/nearai/agents
COPY openapi_client ${LAMBDA_TASK_ROOT}/openapi_client
COPY shared ${LAMBDA_TASK_ROOT}/shared

CMD [ "aws_runner/service.handler" ]