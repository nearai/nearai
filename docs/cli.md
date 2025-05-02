# NEAR AI CLI

NEAR AI CLI allows you to [create and deploy agents](./agents/quickstart.md), [train and test models](./models/home.md), and more!

---

### Requirements

- Python 3.9 - 3.11 **(3.12 - 3.13 is NOT supported)**
- [NEAR Account](#login-to-near-ai)

Additionally, we recommend creating a virtual environment to avoid conflicts with other Python packages.

=== "uv"

    ```bash
    # Create a virtual environment with python 3.11
    uv venv --python 3.11
    source .venv/bin/activate
    ```

=== "conda"

    ```bash
    # Create a virtual environment with python 3.11
    conda create -n nearai python=3.11
    conda activate nearai
    ```

=== "pyenv" 

    ```bash
    # Install python 3.11
    pyenv install 3.11
    pyenv local 3.11

    # Create a virtual environment
    python -m venv .venv
    source .venv/bin/activate
    ```

---

## Installing NEAR AI CLI

=== "pip"

    ``` bash
    pip install nearai  # OR: python3 -m pip install nearai
    ```

=== "local"

    ``` bash
    # Clone the repository:
    git clone git@github.com:nearai/nearai.git
    cd nearai

    # Install dependencies:
    pip install -e .  # OR: python3 -m pip install -e .
    ```


!!! warning "Python version"
    NEAR AI requires python **`3.9 - 3.11`**. We recommend you to [create a virtual environment](#requirements) to avoid conflicts with other Python packages or globally installing dependencies if installing locally w/ repo. 

---


## Login to NEAR AI

To create a new agent, first login with a NEAR Account. If you don't have one, we recommend creating a free account with [Meteor Wallet](https://wallet.meteorwallet.app):

``` bash
nearai login # OR nearai login --remote
```

Example:

``` bash
$> nearai login

Please visit the following URL to complete the login process: https://auth.near.ai?message=Welcome+to+NEAR+AI&nonce=<xyzxyzxyzxyzx>&recipient=ai.near&callbackUrl=http%3A%2F%2Flocalhost%3A63130%2Fcapture
```

After successfully logging in, you will see a confirmation screen. Close it and return to your terminal.


![alt text](./assets/agents/quickstart-login.png)

??? tip "Other Login Methods"

    If you have already logged in on `near-cli`, you know your account's private key, or you have the credentials on another device, you can use the following commands to login:

    ```bash
    ### Login with NEAR Account ID Only
    nearai login --accountId name.near

    ### Login with Account ID and Private Key
    nearai login --accountId name.near --privateKey key

    ### Login Remotely (only displays the login URL)
    nearai login --remote
    ```

---

## Next Steps

That's it! Head over to the [Agent Quickstart](./agents/quickstart.md) to get started creating your first agent! 🚀
