# Publishing AgentTelemetry to PyPI

This document describes how to publish the `agenttelemetry` package to the Python Package Index (PyPI).

---

## Prerequisites

Before publishing, make sure the distribution artifacts have been built:

```bash
# Install the build tool (if not already installed)
pip install build

# Build the source distribution and wheel
python -m build
```

This creates two files in the `dist/` directory:

- `agenttelemetry-0.1.0.tar.gz` -- source distribution (sdist)
- `agenttelemetry-0.1.0-py3-none-any.whl` -- built distribution (wheel)

---

## Step 1: Create a PyPI Account

1. Go to [https://pypi.org/account/register/](https://pypi.org/account/register/).
2. Fill in your username, email, and password.
3. Verify your email address.
4. **Enable two-factor authentication (2FA)** -- PyPI requires 2FA for all accounts that upload packages.

---

## Step 2: Create an API Token

API tokens are the recommended way to authenticate uploads. **Do not use your account password.**

1. Log in at [https://pypi.org/manage/account/](https://pypi.org/manage/account/).
2. Scroll down to the **API tokens** section.
3. Click **Add API token**.
4. Give the token a descriptive name (e.g., `agenttelemetry-upload`).
5. For the first upload, set the scope to **Entire account** (you can scope it to the project after the first successful upload).
6. Click **Create token** and copy the token immediately -- it will not be shown again.
7. The token will start with `pypi-`.

### Storing the Token

You can configure the token so you do not have to enter it every time:

```bash
# Option A: Create/edit ~/.pypirc
cat > ~/.pypirc << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_API_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_API_TOKEN_HERE
EOF

# Restrict permissions on the file
chmod 600 ~/.pypirc
```

**Important:** Never commit `.pypirc` to version control. It contains secrets.

---

## Step 3: Install Twine

Twine is the standard tool for uploading packages to PyPI:

```bash
pip install twine
```

---

## Step 4: Test on Test PyPI First

Test PyPI is a separate instance of PyPI meant for testing. Always upload here first to catch any issues before publishing to the real PyPI.

### 4a. Create a Test PyPI Account

1. Go to [https://test.pypi.org/account/register/](https://test.pypi.org/account/register/).
2. Register a separate account (Test PyPI accounts are independent from PyPI).
3. Create an API token at [https://test.pypi.org/manage/account/](https://test.pypi.org/manage/account/).

### 4b. Upload to Test PyPI

```bash
twine upload --repository testpypi dist/*
```

If you did not configure `~/.pypirc`, you will be prompted for credentials:

```
Username: __token__
Password: pypi-YOUR_TEST_API_TOKEN_HERE
```

### 4c. Verify the Test Upload

Check that the package page exists at:

```
https://test.pypi.org/project/agenttelemetry/
```

Test installing from Test PyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ --no-deps agenttelemetry
```

The `--no-deps` flag is recommended because Test PyPI may not have all dependencies available.

After verifying, uninstall the test version:

```bash
pip uninstall agenttelemetry
```

---

## Step 5: Upload to Production PyPI

Once you have verified the package on Test PyPI, upload to the real PyPI:

```bash
twine upload dist/*
```

If you did not configure `~/.pypirc`, you will be prompted for credentials:

```
Username: __token__
Password: pypi-YOUR_API_TOKEN_HERE
```

### Verify the Upload

Check that the package page exists at:

```
https://pypi.org/project/agenttelemetry/
```

Test installing from PyPI:

```bash
pip install agenttelemetry
```

---

## Step 6: Verify the Published Package

```bash
# Create a fresh virtual environment
python -m venv /tmp/test-agenttelemetry
source /tmp/test-agenttelemetry/bin/activate

# Install and test
pip install agenttelemetry
python -c "import agenttelemetry; print(agenttelemetry.__version__)"

# Test with optional dependencies
pip install agenttelemetry[otlp]

# Clean up
deactivate
rm -rf /tmp/test-agenttelemetry
```

---

## Releasing a New Version

When you are ready to release a new version:

1. **Update the version number** in two places:
   - `pyproject.toml` -- the `version` field under `[project]`
   - `src/agenttelemetry/__init__.py` -- the `__version__` variable

   Both values must match.

2. **Clean old build artifacts:**

   ```bash
   rm -rf dist/ build/ src/agenttelemetry.egg-info/
   ```

3. **Rebuild:**

   ```bash
   python -m build
   ```

4. **Verify the build:**

   ```bash
   twine check dist/*
   ```

5. **Upload** (Test PyPI first, then production PyPI -- see steps 4 and 5 above).

---

## Troubleshooting

### "The user is not allowed to upload to project 'agenttelemetry'"

The package name may already be taken on PyPI. Check at `https://pypi.org/project/agenttelemetry/`. If so, choose a different name in `pyproject.toml`.

### "File already exists"

PyPI does not allow re-uploading the same version. You must bump the version number and rebuild.

### "Invalid distribution"

Run `twine check dist/*` before uploading to catch metadata issues.

### "HTTPError: 403 Forbidden"

Your API token may be expired, revoked, or scoped incorrectly. Generate a new token on PyPI.

---

## Quick Reference

| Action                     | Command                                         |
|----------------------------|--------------------------------------------------|
| Install build tools        | `pip install build twine`                        |
| Build distributions        | `python -m build`                                |
| Check distributions        | `twine check dist/*`                             |
| Upload to Test PyPI        | `twine upload --repository testpypi dist/*`      |
| Upload to production PyPI  | `twine upload dist/*`                            |
| Install from Test PyPI     | `pip install --index-url https://test.pypi.org/simple/ --no-deps agenttelemetry` |
| Install from PyPI          | `pip install agenttelemetry`                     |
