from pylti.common import verify_request_common, LTIException
from fastapi import Request
import os, logging

logger = logging.getLogger(__name__)

LTI_URL = os.getenv("LTI_URL")

def load_lti_credentials():
    consumers = {}
    i = 1
    while True:
        key = os.getenv(f'LTI_CONSUMER_KEY_{i}')
        secret = os.getenv(f'LTI_SHARED_SECRET_{i}')
        if not key or not secret:
            break
        consumers[key] = {"secret": secret}
        i += 1
    return consumers

# Load all LTI consumers at startup
LTI_CONSUMERS = load_lti_credentials()

# LTI Request validation
async def validate_lti_request(request: Request):
    # First, ensure you await the form data from the request
    form_data = await request.form()

    # dictionary of consumers
    consumers = LTI_CONSUMERS
    common_request_verification = False

    try: 
        # Call verify_request_common with all the necessary parameters
        common_request_verification = verify_request_common(
            consumers=consumers,
            url=LTI_URL,#str(request.url),
            method=request.method,
            headers=dict(request.headers),
            params=dict(form_data)  # Ensure this is a dict if not already
        )

    except LTIException as e:
        logger.error(f"LTI validation failed: {e}")

    return common_request_verification