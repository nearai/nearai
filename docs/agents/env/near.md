## Interacting with NEAR Blockchain

The NEAR AI toolkit provides environment methods for interacting with the NEAR blockchain. This framework is designed for seamless integration using a private RPC when running an agent on a NEAR AI hosted runner.

### Features
- Private RPC Integration: NEAR AI provides a private RPC for agents to interact with the NEAR blockchain. This private RPC is optimized for both read operations (e.g., querying contract states) and write operations (e.g., sending transactions or modifying contract state). It ensures secure and reliable communication between hosted agents and the NEAR network, reducing latency and improving overall performance.
- Retry Mechanism: Both view and call methods include a robust retry mechanism to handle transient network or RPC errors.


###  Asyncio and setting Up the Near Account

In order to interact with the blockchain we need to run our agent (or execute our blockchain interactions) in a `asyncio` event loop and set up an Account object from the `py-near` Python library. 
More details: [py-near Account](https://py-near.readthedocs.io/en/latest/account.html#quick-start)


```python
from nearai.agents.environment import Environment
import asyncio

async def run(env: Environment):
    near = env.set_near(account_id, private_key)

    prompt = {"role": "system", "content": ""}
    result = env.completion([prompt] + env.list_messages())

    balance = await near.get_balance("example.near")

    env.add_reply(f"The NEAR balance of example.near is: {balance}")
    env.add_reply(result)

    env.request_user_input()

asyncio.run(run(env))
```


!!! warning "Important"
    Ensure that the `account_id `and `private_key` are never exposed in plain text within the agent's code. We recommend using [secrets](../env/variables.md#managing-secrets) to handle these credentials securely.

**Parameters**:

- `account_id`: The NEAR account ID (e.g., "example.near") that will act as the account for interactions
- `private_key`: The private key associated with the account_id
- `rpc_addr`: (Optional) A custom RPC address for connecting to the NEAR network. If not provided, the default NEAR Mainnet RPC address is used.

**Example**:
```python
near = env.set_near("account.near", "ed25519:3ABCD...XYZ")
```

Once called, the `near` object is ready for use. 


### NEAR VIEW Method

Performs a read-only operation on the NEAR blockchain. This is used to query the state of a contract without modifying it. Examples include retrieving contract states, or querying other read-only data.

The result object contains the transaction details, including the logs and block hash, and any returned values. For more details on the format of the result object, refer to the [py-near](https://py-near.readthedocs.io/en/latest/) documentation.

!!! info "Info"
    `near.view` can be used without providing `account_id` or `private_key` to `env.set_near()`.

```python
near = env.set_near()

await near.view(
    contract_id: str,
    method_name: str,
    args: dict,
    block_id: Optional[int] = None,
    threshold: Optional[int] = None,
    max_retries: int = 3
))
```

**Parameters**:

- `contract_id`: The NEAR account ID of the smart contract you want to query.
- `method_name`: The name of the view method to call on the contract.
- `args`: A dictionary of arguments to pass to the view method.
- `block_id`: (Optional) The block ID to query. Defaults to the latest block.
- `threshold`: (Optional) A threshold parameter for advanced queries.
- `max_retries`: (Optional) The maximum number of retry attempts in case of transient errors (default is 3, max is 10).

**Returns**:

- The result of the view method call, typically containing the queried data.

**Example**:
```python
near = env.set_near()

result = await near.view(
    contract_id="wrap.near",
    method_name="ft_balance_of",
    args={
        "account_id": "user.near"
    }
)

print(result)
print("Wrap.NEAR Balance:", result.result)
```
??? info "Output"
    {'block_hash': 'GT3RNuDyAf88GJKEuedNKAkEqZanfTkt2BhhQ11PXAoJ', 'block_height': 144201901, 'logs': [], 'result': '0'}

    'Wrap.NEAR Balance: 0'

### NEAR CALL Method

Executes a state-changing operation on the NEAR blockchain. This is used to call methods on contracts that can modify state, transfer tokens, or perform other operations requiring gas and/or attached tokens.

The result object contains the transaction details, including the status, transaction hash, and any returned values. For more details on the format of the result object, refer to the [py-near](https://py-near.readthedocs.io/en/latest/) documentation.

```python
near = env.set_near("user.near", "ed25519:3ABCD...XYZ")

await near.call(
    contract_id: str,
    method_name: str,
    args: dict,
    gas: int = DEFAULT_ATTACHED_GAS,
    amount: int = 0,
    nowait: bool = False,
    included: bool = False,
    max_retries: int = 3
))
```

**Parameters**:

- `contract_id`: The NEAR account ID of the smart contract you want to call.
- `method_name`: The name of the method to invoke on the contract.
- `args`: A dictionary of arguments to pass to the method.
- `gas`: (Optional) The amount of gas to attach for execution (default: DEFAULT_ATTACHED_GAS). 
- `amount`: (Optional) The amount of NEAR tokens to attach to the transaction (default: 0). 
- `nowait`: (Optional) If True, the call will not wait for transaction confirmation. 
- `included`: (Optional) If True, ensures the transaction is included in the block before returning.
- `max_retries`: (Optional) The maximum number of retry attempts in case of transient errors (default is 3, max is 10). Use this parameter only if necessary, as there is a risk that the transaction might be sent multiple times.
 
**Returns**:

- The result of the contract method call, including transaction details and status.

**Example**:
```python
near = env.set_near("user.near", "ed25519:3ABCD...XYZ")

result = await near.call(
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


### NEAR GET BALANCE

`get_balance` retrieves the NEAR token balance of a given account. 

**Parameters**:

- `account_id` : (Optional) The ID of the account to retrieve the balance for. If not provided, the balance of the current account is retrieved.

**Example**:
```python
near = env.set_near("alice.near")

print(await near.get_balance())
print(await near.get_balance("bob.near"))
```
