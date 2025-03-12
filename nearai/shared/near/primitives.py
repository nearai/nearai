import datetime
import hashlib
import json

import base58
import pytz


def now():
    return datetime.datetime.now(pytz.utc)


def now_short_humanized():
    return datetime.datetime.now(pytz.utc).strftime("%H:%M:%S")


def str_to_datetime(s):
    try:
        dt = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f+00:00")
    except:  # noqa: E722
        dt = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S+00:00")
    return pytz.timezone("UTC").localize(dt)


# autopep8: off
### DANGER ZONE starts here
#
# Each update of `get_output_hash`, `hash` or `combine_hash` must be processed with
# DB update to keep data representation actual and reachable.
def hash(data):
    return hashlib.sha256(data.encode("utf-8")).digest()


def combine_hash(hash1, hash2):
    return hashlib.sha256(hash1 + hash2).digest()


# `get_output_hash` builds base58-encoded sha256 based on data provided.
# Expected data types:
# - module_id - int, will be transformed into str
# - output_name - str, taken as is
# - inputs - dict of {input_name, base58-decoded input_hash}
# - params - dict of {param_name, param_value}
def get_output_hash(module_id, output_name, inputs=None, params=None):
    if inputs is None:
        inputs = {}
    if params is None:
        params = {}

    # 1. Hashing module_id
    h = hash(str(module_id))

    # 2. Hashing output_name
    h = combine_hash(h, hash(output_name))

    # 3. Hashing inputs. We need to process them in a sorted order and decode from base58
    for input_name in sorted(inputs):
        h = combine_hash(h, base58.b58decode(inputs[input_name]))

    # 4. Hashing params. Make a sorted and as most compact JSON as possible
    params_compact = json.dumps(params, indent=None, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    h = combine_hash(h, hash(params_compact))

    # Result is encoded into base58
    return base58.b58encode(h).decode("utf-8")


def get_unique_id(module_id, inputs=None, params=None):
    if inputs is None:
        inputs = {}
    if params is None:
        params = {}
    return get_output_hash(module_id, "", inputs, params)[:10]


### DANGER ZONE ends here
# autopep8: on
