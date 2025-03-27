# NEAR AI CLI

NEAR AI CLI allows you to [create and deploy agents](./agents/quickstart.md), [train and test models](./models/home.md), and more!

---

!!! warning
    Requires Python version **`3.9 - 3.11`** _(Currently does not work with `3.12` or `3.13`)_

!!! abstract "Python Version Management"

    New to Python or don't have a compatible version? Try using a version management tool as they allow you to easily install and switch between Python versions. 
    
    Here are some popular options:
    
    - [uv](https://docs.astral.sh/uv/) - Fast Python package manager _(Preferred tool by `nearai` core contributors)_
    - [pyenv](https://github.com/pyenv/pyenv) - Simple Python version management tool
    - [miniconda](https://docs.anaconda.com/miniconda/install/) - Miniature installation of Anaconda Distribution 

## Installing NEAR AI CLI

=== "pip"

    ``` bash
    python3 -m pip install nearai
    ```

=== "local"

    Clone project:
    
    ``` bash
    git clone git@github.com:nearai/nearai.git
    cd nearai
    ```
    
    Install `nearai`:

    === "Install Script"

        ```bash
        ./install.sh
        ```

        This script uses Python3's built in virtual environment creator `venv`.
        
        **Please ensure you are using Python `3.9-3.11` before running.**

    === "uv"

        Download, create, and activate a virtual Python `3.11` environment:

        ```bash
        uv venv --python 3.11
        source .venv/bin/activate
        ```
        
        Install `nearai` from repo:
        
        ```bash
        pip install -e .
        ```

    === "conda"

        Download, create, and activate a virtual Python `3.11` environment:
        
        ```bash
        conda create -n nearai python=3.11
        conda activate nearai
        ```

        Install `nearai` from local repo:
        ```bash
        pip install -e .
        ```

    === "pyenv" 

        If needed, install Python `3.11` with `pyenv`:

        ```bash
        pyenv install 3.11
        ```

        Set local version to `3.11`:
        
        ```bash
        pyenv local 3.11
        ```
        
        Create and activate a virtual environment:
        
        ```bash
        python -m venv .venv
        source .venv/bin/activate
        ```

        Install `nearai` from local repo:

        ```bash
        pip install --upgrade pip
        pip install -e .
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