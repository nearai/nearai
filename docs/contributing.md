# Contribute to `nearai`

Everyone is welcome to contribute, and we value everybody's contribution. Code
contributions are not the only way to help the community. Answering questions, helping
others, and improving documentation are also immensely valuable.

It also helps us if you spread the word! Reference the library in blog posts
about the awesome projects it made possible, or even simply ⭐️ the repository to say thank you.

**This guide was heavily inspired by the [huggingface transformers guide to contributing](https://github.com/huggingface/transformers/blob/main/CONTRIBUTING.md).**

---

# Ways to contribute

There are several ways you can contribute to `nearai`:

- [Contribute to `nearai`](#contribute-to-nearai)
- [Ways to contribute](#ways-to-contribute)
  - [Fixing outstanding issues](#fixing-outstanding-issues)
  - [Submitting a bug-related issue or feature request](#submitting-a-bug-related-issue-or-feature-request)
    - [Did you find a bug?](#did-you-find-a-bug)
    - [Do you want a new feature?](#do-you-want-a-new-feature)
  - [Contribute Documentation](#contribute-documentation)
  - [Create a Pull Request](#create-a-pull-request)
    - [Pull request checklist](#pull-request-checklist)
    - [Sync a forked repository with upstream main](#sync-a-forked-repository-with-upstream-main)

## Fixing outstanding issues

If you notice an issue with the existing code and have a fix in mind, feel free to [start contributing](#create-a-pull-request) and open a Pull Request!

## Submitting a bug-related issue or feature request

Do your best to follow these guidelines when submitting a bug-related issue or a feature
request. It will make it easier for us to come back to you quickly and with good
feedback.

### Did you find a bug?

`nearai` is alpha software. This means there is a possibility of encountering issues in the code. With help from users like you who report problems, we can make it more robust and reliable.

Before you report an issue, we would really appreciate it if you could **make sure the bug was not
already reported** (use the search bar on GitHub under Issues). Your issue should also be related to bugs in the library itself, and not your code.

Once you've confirmed the bug hasn't already been reported, please include the following information in your issue so we can quickly resolve it:

* What did you do?
* What did you expect to happen?
* What happened instead?
* Your **OS type and version** and **Python**, **PyTorch** and versions where applicable.
* A short, self-contained, code snippet that allows us to reproduce the bug in
  less than 30s.
* The *full* traceback if an exception is raised.
* Attach any other additional information, like screenshots, you think may help.

To get the OS and software versions automatically, run the following command:

```bash
uname -a
```

### Do you want a new feature?

If there is a new feature you'd like to see in `nearai`, please open an issue and describe:

1. What is the *motivation* behind this feature? Is it related to a problem or frustration with the library? Is it a feature related to something you need for a project? Is it something you worked on and think it could benefit the community?

   Whatever it is, we'd love to hear about it!

2. Describe your requested feature in as much detail as possible. The more you can tell us about it, the better we'll be able to help you.
3. Provide a *code snippet* that demonstrates the feature usage.
4. If the feature is related to a paper, please include a link.

## Contribute Documentation

If you discover any errors or omissions in our documentation, please open an issue and describe:

* Which explanation or code snippet is incorrect
* What concept is not clear or missing
* If you know, what would be the correct explanation or code snippet

If you think you can contribute a fix for the issue, please feel free to open a Pull Request.

To preview your changes locally, you will need to install all the dependencies for the documentation which can be easily installed through `pip` or `uv`:

=== "pip"

      ```bash
      pip install -e ".[docs]"
      ```

=== "uv"
      ```bash
      uv sync --group docs
      ```

Then simply test your changes locally using `mkdocs serve`

!!! failure "Cairo Graphics"

      If you encounter a problem with `cairo`, please follow the [mkdocs-material Requirements Guide](https://squidfunk.github.io/mkdocs-material/plugins/requirements/image-processing/#cairo-graphics)


## Create a Pull Request

Before writing any code, we strongly advise you to search through the existing PRs or
issues to make sure nobody is already working on the same thing. If you are
unsure, it is always a good idea to open an issue to get some feedback.

You will need basic `git` proficiency to contribute to
`nearai`. While `git` is not the easiest tool to use, it has the greatest
manual. Type `git --help` in a shell and enjoy! If you prefer books, [Pro
Git](https://git-scm.com/book/en/v2) is a very good reference. We also recommend
asking any available AGI to help you with `git`.

Follow the steps below to start contributing:

1. Fork the [repository](https://github.com/nearai/nearai) by
   clicking on the **[Fork](https://github.com/nearai/nearai/fork)** button on the repository's page. This creates a copy of the code
   under your GitHub user account.

2. Clone your fork to your local disk, and add the base repository as a remote:

   ```bash
   git clone git@github.com:<your Github handle>/nearai.git
   cd nearai
   git remote add upstream https://github.com/nearai/nearai.git
   ```

3. Create a new branch to hold your development changes:

   ```bash
   git checkout -b a-descriptive-name-for-my-changes
   ```

   🚨 **Do not** work on the `main` branch!

4. Set up a development environment (follow steps in the [README](https://github.com/nearai/nearai)):

5. Develop the features in your branch.

   As you work on your code, you should make sure it functions as intended.

   `nearai` relies on [`ruff`](https://docs.astral.sh/ruff/) and [`mypy`](https://mypy.readthedocs.io/en/stable/) to format and type check its source code
   consistently. After you make your changes and are ready to PR them, ensure that
   your code is formatted and type-checked by running:
    
   ```bash
   ./scripts/format_check.sh
   ```
   
   ```bash
   ./scripts/lint_check.sh
   ```

   ```bash
   ./scripts/type_check.sh
   ```

   Once you're happy with your changes, add the changed files with `git add` and
   record your changes locally with `git commit`:

   ```bash
   git add modified_file.py
   git commit
   ```

   Please remember to write [good commit
   messages](https://chris.beams.io/posts/git-commit/) to clearly communicate the changes you made!

   To keep your copy of the code up to date with the original
   repository, rebase your branch on `upstream/branch` *before* you open a pull request or if requested by a maintainer:

   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

   Push your changes to your branch:

   ```bash
   git push -u origin a-descriptive-name-for-my-changes
   ```

   If you've already opened a pull request, you'll need to force push with the `--force` flag. Otherwise, if the pull request hasn't been opened yet, you can just push your changes normally.

6. Now you can go to your fork of the repository on GitHub and click on **Pull Request** to open a pull request. Make sure you tick off all the boxes on our [checklist](#pull-request-checklist) below. When you're ready, you can send your changes to the project maintainers for review.

7. It's ok if maintainers request changes, it happens to our core contributors
   too! So everyone can see the changes in the pull request, work in your local
   branch and push the changes to your fork. They will automatically appear in
   the pull request.

### Pull request checklist

- The pull request title should summarize your contribution.<br>
- If your pull request addresses an issue, please mention the issue number in the pull
request description to make sure they are linked (and people viewing the issue know you
are working on it).<br>
- To indicate a work in progress please prefix the title with `[WIP]`. These are
useful to avoid duplicated work, and to differentiate it from PRs ready to be merged.<br>
- Don't add any images, videos and other non-text files that'll significantly weigh down the repository. Instead, reference them by URL.

### Sync a forked repository with upstream main

When updating the main branch of a forked repository, please follow these steps to avoid pinging the upstream repository which adds reference notes to each upstream PR, and sends unnecessary notifications to the developers involved in these PRs.

1. When possible, avoid syncing with the upstream using a branch and PR on the forked repository. Instead, merge directly into the forked main.
2. If a PR is absolutely necessary, use the following steps after checking out your branch:

   ```bash
   git checkout -b your-branch-for-syncing
   git pull --squash --no-commit upstream main
   git commit -m '<your message without GitHub references>'
   git push --set-upstream origin your-branch-for-syncing
   ```