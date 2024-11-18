FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN pip install flask salesforce-lavis

# Download Stanza models (for English in this example)
RUN python -c "import stanza; stanza.download('en')"

# Copy the middleware code
COPY main.py .

# Expose the middleware port
EXPOSE 5001

# Run the middleware
CMD ["python", "main.py"]

