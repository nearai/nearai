# NEAR AI CLI

The NEAR AI CLI allows you to interact with NEAR AI's services to [create agents](./agents/quickstart.md) or [train and test models](./models/home.md). Let's quickly review how to install it and login with your NEAR account.

!!! tip
    Do you want to build an agent? Install the CLI, login, and then check our [**Agent Quickstart Guide**](./agents/quickstart.md).

!!! info
    Remember that you can use NEAR AI from the [Web Hub](https://hub.near.ai), the NEAR AI CLI is targeted at developers who want to build their own agents or train models on NEAR AI.

---

## Installing NEAR AI CLI

=== "pip"

    ``` bash
    python3 -m pip install nearai
    ```

=== "local"

    ``` bash
    git clone git@github.com:nearai/nearai.git
    cd nearai
    pip install -e .
    ```

??? abstract "Python Version"

    If you do not have python, or your version is not compatible, we recommend that you use [miniconda](https://docs.anaconda.com/miniconda/install/) or [pyenv](https://github.com/pyenv/pyenv)
    to manage your installations, as they both allow you to easily switch between python versions.

    === "pyenv"

        ``` bash
        pyenv install 3.11
        pyenv local 3.11 # or use global
        ```

    === "conda"

        ``` bash
        conda create -n myenv python=3.11
        conda activate myenv
        ```

---

## Login to NEAR AI

To create a new agent, first login with a [NEAR Account](https://wallet.near.org/):

``` bash
nearai login
```

??? tip "Don't have a NEAR Account?"

    If you do not have a NEAR account, you can create one for free using wallets listed at [wallet.near.org](https://wallet.near.org/). 
    
    If you are unsure of which one to choose, try out [Bitte](https://wallet.bitte.ai) or [Meteor Wallet](https://wallet.meteorwallet.app/add_wallet/create_new).

You'll be provided with a URL to login with your NEAR account.

Example:

``` bash
$> nearai login

Please visit the following URL to complete the login process: https://auth.near.ai?message=Welcome+to+NEAR+AI&nonce=<xyzxyzxyzxyzx>&recipient=ai.near&callbackUrl=http%3A%2F%2Flocalhost%3A63130%2Fcapture
```

After successfully logging in, you will see a confirmation screen. Close it and return to your terminal.


![alt text](./assets/agents/quickstart-login.png)

??? tip Other Login Methods

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

That's it! You're now ready to create your first agent. Head over to the [Agents Guide](./agents/quickstart.md) to get started.