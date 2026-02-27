from pylti.common import verify_request_common, LTIException
from fastapi import Request
import os, logging

logger = logging.getLogger(__name__)

def load_lti_credentials():
    consumers = {}
    for env_key, value in os.environ.items():
        if env_key.startswith("LTI_CONSUMER_KEY_"):
            suffix = env_key.rsplit("_", 1)[-1]
            secret = os.getenv(f"LTI_SHARED_SECRET_{suffix}")
            if value and secret:
                consumers[value] = {"secret": secret}
    return consumers

#LTI Request validation
async def validate_lti_request(request: Request):
    # First, ensure you await the form data from the request
    form_data = await request.form()
    # dictionary of consumers
    common_request_verification = False

    LTI_URL = os.getenv("LTI_URL")
    LTI_CONSUMERS = load_lti_credentials()
    if not LTI_URL or not LTI_CONSUMERS:
        logger.error("LTI_URL or LTI_CONSUMERS not properly configured in environment variables.")
        return False

    request_url = str(request.url)
    
    request_url_no_port = request_url
    scheme, rest = request_url.split("//", 1)
    if ":" in request_url.split("//", 1)[-1]:
        host = rest.split("/", 1)[0]
        host_without_port = host.split(":")[0]
        path = rest[len(host):]
        request_url_no_port = f"{scheme}//{host_without_port}{path}"
    candidate_urls = [request_url]

    if "sqlapp2" in request_url:
        request_url_wo_secured = "http://backend/sqlapp2/lti/login"
        candidate_urls.append(request_url_wo_secured)
    
    if "https" in LTI_URL:
        lti_url_wo_secured = LTI_URL.replace("https:","http:")
        candidate_urls.append(lti_url_wo_secured)

    if request_url_no_port != request_url:
        candidate_urls.append(request_url_no_port)
    if LTI_URL:
        candidate_urls.append(LTI_URL)

    tried_urls = []
    for url_candidate in candidate_urls:
        url_candidate = url_candidate.rstrip("/")
        if url_candidate in tried_urls:
            continue
        tried_urls.append(url_candidate)
        logger.debug(f"Attempting LTI verification with URL: {url_candidate}")
        try:
            common_request_verification = verify_request_common(
                consumers=LTI_CONSUMERS,
                url=url_candidate,
                method=request.method,
                headers=dict(request.headers),
                params=dict(form_data)  # pylti expects a dict-like object
            )
            if common_request_verification:
                logger.info(
                    "LTI verification succeeded using URL %s (consumer_key=%s)",
                    url_candidate,
                    form_data.get("oauth_consumer_key"),
                )
                return True
        except LTIException as e:
            logger.warning(
                "LTI verification failed for URL %s (consumer_key=%s): %s",
                url_candidate,
                form_data.get("oauth_consumer_key"),
                e,
            )

            logger.error(f"LTI_URL: {LTI_URL}")
            logger.error(f"request URL: {request.url}")
            #logger.error(f"LTI_CONSUMERS: {LTI_CONSUMERS}")
            logger.error(f"request.method: {request.method}")
            logger.error(f"request.headers: {request.headers}")
            logger.error(f"form_data: {form_data}")
    logger.error("LTI validation failed for all candidate URLs.")

    return False


# async def validate_lti_request(request: Request):
#     form_data = dict(await request.form())
#     consumers = load_lti_credentials()

#     proto = request.headers.get("x-forwarded-proto", request.url.scheme)
#     host = request.headers.get("x-forwarded-host", request.headers.get("host"))
#     root_path = request.scope.get("root_path", "")
#     path = (
#         f"{root_path}{request.url.path}"
#         if root_path and not request.url.path.startswith(root_path)
#         else request.url.path
#     )
#     public_url = f"{proto}://{host}{path}".rstrip("/")

#     headers = dict(request.headers)
#     if "x-forwarded-proto" in headers:
#         headers["X-Forwarded-Proto"] = headers["x-forwarded-proto"]

#     print("=== LTI validate_lti_request debug start ===")
#     print("request.url           =", str(request.url))
#     print("request.method        =", request.method)
#     print("request.url.scheme    =", request.url.scheme)
#     print("x-forwarded-proto     =", request.headers.get("x-forwarded-proto"))
#     print("x-forwarded-host      =", request.headers.get("x-forwarded-host"))
#     print("host                  =", request.headers.get("host"))
#     print("root_path             =", root_path)
#     print("request.url.path      =", request.url.path)
#     print("computed path         =", path)
#     print("public_url            =", public_url)
#     print("consumer keys loaded  =", list(consumers.keys()))
#     print("oauth_consumer_key    =", form_data.get("oauth_consumer_key"))
#     print("oauth_signature       =", form_data.get("oauth_signature"))
#     print("form_data             =", form_data)
#     print("headers               =", headers)

#     try:
#         result = verify_request_common(
#             consumers=consumers,
#             url=public_url,
#             method=request.method,
#             headers=headers,
#             params=form_data,
#         )
#         print("verify_request_common =", result)
#         print("=== LTI validate_lti_request debug end ===")
#         return result

#     except LTIException as e:
#         print("LTIException occurred =", str(e))
#         print("public_url            =", public_url)
#         print("=== LTI validate_lti_request debug end (exception) ===")
#         logger.warning("LTI verification failed: %s", e)
#         logger.error("public_url=%s", public_url)
#         return False