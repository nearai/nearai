FROM public.ecr.aws/lambda/python:3.12

# pass with --build-arg FRAMEWORK=-langgraph
ARG FRAMEWORK=""

COPY aws_runner/frameworks/requirements${FRAMEWORK}.txt ${LAMBDA_TASK_ROOT}

RUN pip install -r requirements${FRAMEWORK}.txt

# Runner code
COPY aws_runner/service.py aws_runner/partial_near_client.py ${LAMBDA_TASK_ROOT}
COPY aws_runner/runner ${LAMBDA_TASK_ROOT}/runner
COPY openapi_client ${LAMBDA_TASK_ROOT}/openapi_client
COPY shared ${LAMBDA_TASK_ROOT}/shared

CMD [ "service.handler" ]