import json


class LambdaWrapper:
    def __init__(self, lambda_client):
        """Initialize LambdaWrapper with a client for invoking lambdas."""
        self.lambda_client = lambda_client

    def invoke_function(self, function_name, function_params, get_log=False):
        """Invokes a Lambda function.

        :param function_name: The name of the function to invoke.
        :param function_params: The parameters of the function as a dict. This dict
                                is serialized to JSON before it is sent to Lambda.
        :param get_log: When true, the last 4 KB of the execution log are included in
                        the response.
        :return: The response from the function invocation.
        """
        # convert function_params.auth.nonce from bytes into text
        if function_params.get("auth") and function_params["auth"].get("nonce"):
            if isinstance(function_params["auth"]["nonce"], bytes):
                function_params["auth"]["nonce"] = function_params["auth"]["nonce"].decode("utf-8")

        response = self.lambda_client.invoke(
            FunctionName=function_name,
            Payload=json.dumps(function_params),
            LogType="Tail" if get_log else "None",
            InvocationType="RequestResponse",
        )
        data = response["Payload"].read()
        if data:
            data = data.decode("utf-8")
            return data
        else:
            raise ValueError("No data returned from Lambda function")
