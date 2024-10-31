from unittest import TestCase

import nearai.agents.tool_json_helper as j

DEFAULT_SIGNATURE = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Get the current weather in a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state, e.g. San Francisco, CA",
                },
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["location"],
        },
    },
}


class Test(TestCase):
    def test_parse_json_args(self):  # noqa: D102
        args = j.parse_json_args(DEFAULT_SIGNATURE, '{"location": "San Francisco, CA", "unit": "celsius"}')
        self.assertEqual(args, {"location": "San Francisco, CA", "unit": "celsius"})

    def test_parse_json_args_empty(self):  # noqa: D102
        with self.assertRaises(ValueError):
            _args = j.parse_json_args(DEFAULT_SIGNATURE, "")

    def test_parse_json_args_empty_no_arg_function(self):  # noqa: D102
        no_arg_function_signature = {
            "type": "function",
            "function": {
                "name": "say_hi",
                "description": "Says 'hi!'",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }
        args = j.parse_json_args(no_arg_function_signature, "")
        self.assertEqual(args, {})

    def test_parse_json_args_invalid(self):  # noqa: D102
        with self.assertRaises(ValueError):
            j.parse_json_args(DEFAULT_SIGNATURE, '{"a": 1, "b": 2')

    def test_parse_json_args_trailing_quote(self):  # noqa: D102
        args = j.parse_json_args(DEFAULT_SIGNATURE, '{"location": "San Francisco, CA", "unit": "celsius"}"')
        self.assertEqual(args, {"location": "San Francisco, CA", "unit": "celsius"})

    def test_parse_json_args_trailing_brace(self):  # noqa: D102
        args = j.parse_json_args(DEFAULT_SIGNATURE, '{"location": "San Francisco, CA", "unit": "celsius"}}')
        self.assertEqual(args, {"location": "San Francisco, CA", "unit": "celsius"})

    def test_parse_json_args_unescaped_quotes(self):  # noqa: D102
        args = j.parse_json_args(DEFAULT_SIGNATURE, '{"location": "San Francisco, "CA"", "unit": "celsius"}')
        self.assertEqual(args, {"location": 'San Francisco, "CA"', "unit": "celsius"})

    def test_parse_json_args_html(self):  # noqa: D102
        write_file_signature = {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "The name of the file"},
                        "content": {"type": "string", "description": "The content of the file"},
                    },
                    "required": ["filename", "content"],
                },
            },
        }
        params = '{"filename": "index.html", "content": "<!DOCTYPE html><html><head><title>Vehicle Maintenance Tracker</title></head><body><h1>Vehicle Maintenance Tracker</h1><form id=", "vehicle-make": "Make:", "vehicle-model": "Model:", "vehicle-year": "Year:", "maintenance-table": "Maintenance Table", "script.js": "Script.js"}'  # noqa: E501
        args = j.parse_json_args(write_file_signature, params)
        # note that in this case a double quote is stripped from the end of the content due to the invalid json
        self.assertEqual(
            args,
            {
                "filename": "index.html",
                "content": '<!DOCTYPE html><html><head><title>Vehicle Maintenance Tracker</title></head><body><h1>Vehicle Maintenance Tracker</h1><form id=", "vehicle-make": "Make:", "vehicle-model": "Model:", "vehicle-year": "Year:", "maintenance-table": "Maintenance Table", "script.js": "Script.js',  # noqa: E501
            },
        )
