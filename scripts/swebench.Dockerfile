# Sandbox image for the SWE-bench subset: a slim Python with pytest installed.
# The repos are bind-mounted into /workspace at run time; a root conftest.py
# (added by build_swebench_subset.py) makes the src/-layout package importable.
FROM python:3.11-slim

# git is required by verification (git apply). Point apt at a China Debian
# mirror so the install doesn't hang on deb.debian.org in constrained networks.
RUN sed -i 's@deb.debian.org@mirrors.tuna.tsinghua.edu.cn@g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Use a configurable pip index (mirror for constrained networks).
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" pytest
