FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt ${LAMBDA_TASK_ROOT}

RUN pip install -r requirements.txt

# Runner code
COPY service.py partial_near_client.py ${LAMBDA_TASK_ROOT}
COPY runner ${LAMBDA_TASK_ROOT}/runner
COPY openapi_client ${LAMBDA_TASK_ROOT}/openapi_client

CMD [ "service.handler" ]