FROM python:3.12-slim

WORKDIR /app

# Install system dependencies and build tools
RUN apt-get update && apt-get install -y curl build-essential && rm -rf /var/lib/apt/lists/*

# Install uv (Astral Python runner)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python build module
RUN pip install --upgrade pip
RUN pip install build

# Copy project files
COPY pyproject.toml ./
COPY aria ./aria

# Build the aria package
RUN python -m build

# Install the built wheel
RUN pip install dist/aria-*.whl

# Create uploads directory
RUN mkdir -p /app/aria/uploads

EXPOSE 8000

CMD ["aria", "run"]
