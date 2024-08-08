# Contributing Guide

## Setting up the project

Build is currently supported only on Debian-based distributions (e.g. Ubuntu).

To clone this repo, run

```
git clone https://github.com/code-genome/codegenome.git
cd codegenome
git submodule update --init --recursive
```

Create a virtual environment.

```
python -mvenv .venv
. .venv/bin/activate
```

Install dependencies.

```
make deps
```

Install requirements.

```
pip install -r requirements.txt
```

Test run the CLI tool.

```
python script/cg genediff /bin/chmod /bin/chown
```


## Running pre-commit before committing

First, install the pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

To run pre-commit before committing:

```bash
pre-commit run --all-files
```

Or simply run:

```bash
make pre-commit
```

This will run the pre-commit hooks on all files.

The pre-commit hooks will:
1. Check for any linting errors
2. Check for any formatting errors
3. Check for any security vulnerabilities
4. Check for spelling errors
4. Verify you used relative imports inside src/ directory
5. Verify you used library imports outside src/ directory

## Running Tests


```
cd tests
python unit_tests.py
```

# Repo principles:

## Git

## Legal

We have tried to make it as easy as possible to make contributions. This applies to how we handle the legal aspects of contribution. We use the same approach - the Developer's Certificate of Origin 1.1 (DCO) - that the Linux® Kernel community uses to manage code contributions.

We simply ask that when submitting a patch for review, the developer must include a sign-off statement in the commit message.

Here is an example Signed-off-by line, which indicates that the submitter accepts the DCO:

Signed-off-by: John Doe <john.doe@example.com>
You can include this automatically when you commit a change to your local git repository using the following command:

git commit -s

### Commit
Always commit with a [good commit message](https://cbea.ms/git-commit/) and sign off:

Example:

```bash
git commit -s
```

### Push
Push into a new branch and open a PR.

Example:

```bash
git push origin main:<my-new-branch-name>
```
