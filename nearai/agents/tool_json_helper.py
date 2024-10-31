import json
import re


def _ending_transform(x):
    if x.endswith('}"') or x.endswith("}}"):
        return json.loads(x[:-1])
    else:
        raise json.JSONDecodeError("Try next transform", x, len(x))


def parse_json_args(signature: dict, args: str):
    """Parses LLM generated JSON args, trying various repair strategies if args are not valid JSON."""
    # if args is empty or an empty json object check if the function has no arguments
    if not args or args == "{}":
        if not signature["function"]["parameters"]["required"]:
            return {}
        else:
            raise ValueError("Function requires arguments")

    transforms = [
        lambda x: json.loads(x),
        _ending_transform,
        lambda x: parse_json_args_based_on_signature(signature, x),
    ]

    for transform in transforms:
        try:
            result = transform(args)
            # check that all result keys are valid properties in the signature
            for key in result.keys():
                if key not in signature["function"]["parameters"]["properties"]:
                    raise json.JSONDecodeError(f"Unknown parameter {key}", args, 0)
            return result
        except json.JSONDecodeError:
            continue
        except Exception as err:
            raise json.JSONDecodeError("Error parsing function args", args, 0) from err


def parse_json_args_based_on_signature(signature: dict, args: str):
    """Finds parameter names based on the signature and tries to extract the values in between from the args string."""
    parameter_names = list(signature["function"]["parameters"]["properties"].keys())
    # find each parameter name in the args string
    #   assuming each parameter name is surrounded by "s, followed by a colon and optionally preceded by a comma,
    #   extract the intervening values as values
    parameter_positions = {}
    parameter_values = {}
    for param in parameter_names:
        match = re.search(f',?\\s*"({param})"\\s*:', args)
        if not match:
            raise ValueError(f"Parameter {param} not found in args {args}")
        parameter_positions[param] = (match.start(), match.end())
    # sort the parameter positions by start position
    sorted_positions = sorted(parameter_positions.items(), key=lambda x: x[1][0])
    # for each parameter, extract the value from the args string
    for i, (param, (start, end)) in enumerate(sorted_positions):  # noqa B007
        # if this is the last parameter, extract the value from the start position to the end of the string
        if i == len(sorted_positions) - 1:
            raw_value = args[end:-1]
            if raw_value.endswith("}"):
                raw_value = raw_value[:-1]
        # otherwise, extract the value from the start position to the start position of the next parameter
        else:
            next_start = sorted_positions[i + 1][1][0]
            raw_value = args[end:next_start]
        raw_value = raw_value.strip()
        if raw_value.startswith('"') and raw_value.endswith('"'):
            raw_value = raw_value[1:-1]
        parameter_values[param] = raw_value
    return parameter_values
