FROM public.ecr.aws/lambda/python:3.12

# pass with --build-arg FRAMEWORK=-langgraph
ARG FRAMEWORK=""

COPY frameworks/requirements${FRAMEWORK}.txt ${LAMBDA_TASK_ROOT}

RUN pip install -r requirements${FRAMEWORK}.txt

# Runner code
COPY service.py partial_near_client.py ${LAMBDA_TASK_ROOT}
COPY runner ${LAMBDA_TASK_ROOT}/runner
COPY openapi_client ${LAMBDA_TASK_ROOT}/openapi_client

CMD [ "service.handler" ]