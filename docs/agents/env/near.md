## Interacting with NEAR Blockchain

The NEAR AI toolkit provides environment methods for interacting with the NEAR blockchain. This framework is designed for seamless integration using a private RPC when running an agent on a NEAR AI hosted runner.

### Features
- Private RPC Integration: NEAR AI provides a private RPC for agents to interact with the NEAR blockchain. This private RPC is optimized for both read operations (e.g., querying contract states) and write operations (e.g., sending transactions or modifying contract state). It ensures secure and reliable communication between hosted agents and the NEAR network, reducing latency and improving overall performance.
- Retry Mechanism: Both view and call methods include a robust retry mechanism to handle transient network or RPC errors.


### Setting Up the Near Account

```
env.set_near(account_id, private_key)
```

This method initializes the env.near object, allowing you to interact with the NEAR blockchain.

!!! warning "Important"
    Ensure that the `account_id `and `private_key` are never exposed in plain text within the agent's code. We recommend using [secrets](../secrets.md) to handle these credentials securely.

Parameters:
- `account_id`: The NEAR account ID (e.g., "example.near") that will act as the account for interactions
- `private_key`: The private key associated with the account_id
- `rpc_addr`: (Optional) A custom RPC address for connecting to the NEAR network. If not provided, the default NEAR RPC address is used.

- Example:
```
env.set_near("account.near", "ed25519:3ABCD...XYZ")
```

Once called, the `env.near` object is ready for use. Note that `near.view` can be used without calling `env.set_near()`.

### NEAR VIEW Method

`env.near.view` performs a read-only operation on the NEAR blockchain. This is used to query the state of a contract without modifying it. Examples include retrieving contract states, or querying other read-only data.

The result object contains the transaction details, including the logs and block hash, and any returned values. For more details on the format of the result object, refer to the [py-near](https://py-near.readthedocs.io/en/latest/) documentation.

```
await env.near.view(
    contract_id: str,
    method_name: str,
    args: dict,
    block_id: Optional[int] = None,
    threshold: Optional[int] = None,
    max_retries: int = 3
)
```

Parameters:
- `contract_id`: The NEAR account ID of the smart contract you want to query.
- `method_name`: The name of the view method to call on the contract.
- `args`: A dictionary of arguments to pass to the view method.
- `block_id`: (Optional) The block ID to query. Defaults to the latest block.
- `threshold`: (Optional) A threshold parameter for advanced queries.
- `max_retries`: (Optional) The maximum number of retry attempts in case of transient errors (default is 3, max is 10).

Returns:
- The result of the view method call, typically containing the queried data.

Example:
```
env.set_near("user.near", "ed25519:3ABCD...XYZ")
result = await env.near.view(
    contract_id="wrap.near",
    method_name="ft_balance_of",
    args={
        "account_id": "user.near"
    }
)

print("Wrap.NEAR Balance:", result.result)
```

### NEAR CALL Method

`near.call` executes a state-changing operation on the NEAR blockchain. This is used to call methods on contracts that can modify state, transfer tokens, or perform other operations requiring gas and/or attached tokens.

The result object contains the transaction details, including the status, transaction hash, and any returned values. For more details on the format of the result object, refer to the [py-near](https://py-near.readthedocs.io/en/latest/) documentation.

```
await env.near.call(
    contract_id: str,
    method_name: str,
    args: dict,
    gas: int = DEFAULT_ATTACHED_GAS,
    amount: int = 0,
    nowait: bool = False,
    included: bool = False,
    max_retries: int = 3
)
```

Parameters:
- `contract_id`: The NEAR account ID of the smart contract you want to call.
- `method_name`: The name of the method to invoke on the contract.
- `args`: A dictionary of arguments to pass to the method.
- `gas`: (Optional) The amount of gas to attach for execution (default: DEFAULT_ATTACHED_GAS). 
- `amount`: (Optional) The amount of NEAR tokens to attach to the transaction (default: 0). 
- `nowait`: (Optional) If True, the call will not wait for transaction confirmation. 
- `included`: (Optional) If True, ensures the transaction is included in the block before returning.
- `max_retries`: (Optional) The maximum number of retry attempts in case of transient errors (default is 3, max is 10). Use this parameter only if necessary, as there is a risk that the transaction might be sent multiple times.
 
Returns:
- The result of the contract method call, including transaction details and status.

Example:
```
result = await env.near.call(
    contract_id="wrap.near",
    method_name="ft_transfer",
    args={
        "receiver_id": "example.near",
        "amount": "1000000"
    },
    gas=30000000000000,
    amount=1
)

if "SuccessValue" in result.status:
    print("tx", result.transaction.hash)
```