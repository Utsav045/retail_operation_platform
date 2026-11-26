"""
Unified Error Architecture & User-Friendly Exception Handler.
Translates technical, database, and hardware store codes into plain-English,
actionable messages with uniform structure across the entire platform.
"""
from typing import Optional, Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


# Master Store Hub & POS Hardware Error Code Dictionary
HUB_ERROR_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "E301": {
        "title": "Corrupt File Structure",
        "message": "The transaction file format is damaged or has missing XML/JSON tags. The system has safely isolated it in the quarantine vault.",
        "user_action": "Inspect the raw file in the System Health vault or request a clean batch re-export from the store server."
    },
    "E302": {
        "title": "Duplicate Batch Detected",
        "message": "This transaction batch has already been processed into the store ledger. Duplicate processing was prevented to avoid double-counting sales.",
        "user_action": "No action needed. The system successfully verified batch idempotency."
    },
    "E312": {
        "title": "Missing Product Variant Code",
        "message": "The store cash registers require a 3-digit variant code (such as '000') for every item.",
        "user_action": "Add the 3-digit variant code (e.g., '000') to the product catalog before re-publishing."
    },
    "E315": {
        "title": "Product Description Too Long",
        "message": "The product name exceeds the 24-character display limit of register screens.",
        "user_action": "Shorten the product description to 24 characters or less so it fits on cash register displays."
    },
    "E318": {
        "title": "Price Limit Safety Violation",
        "message": "The submitted price exceeds the store safety limit (maximum allowed single item price is $999.99).",
        "user_action": "Verify the unit price decimal point to ensure high-value items are entered accurately."
    },
    "E402": {
        "title": "Item Not In Master Catalog",
        "message": "A scanned item code does not exist in the central store product catalog.",
        "user_action": "Add the missing item to the central price book before processing sales for this SKU."
    },
    "E410": {
        "title": "Commercial Credit Limit Exceeded",
        "message": "The commercial account balance exceeds its approved credit ceiling.",
        "user_action": "Review the monthly statement and record an incoming customer payment to restore available credit."
    }
}


class AppException(Exception):
    """
    Standardized Application Exception for all user-facing errors.
    Provides uniform error code, plain-English message, and clear next steps.
    """
    def __init__(
        self,
        code: str,
        message: str,
        user_action: str = "Please verify your input or contact the store operations team.",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Any] = None
    ):
        self.code = code
        self.message = message
        self.user_action = user_action
        self.status_code = status_code
        self.details = details
        super().__init__(message)


def build_error_response(
    status_code: int,
    code: str,
    message: str,
    user_action: str,
    details: Optional[Any] = None
) -> JSONResponse:
    """Constructs a consistent, user-identical error payload across all endpoints."""
    return JSONResponse(
        status_code=status_code,
        content={
            # Standard 'detail' maintained for backwards compatibility with test fixtures
            "detail": message,
            "error": {
                "code": code,
                "message": message,
                "user_action": user_action,
                "status_code": status_code,
                "details": details
            }
        }
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handles explicit AppExceptions."""
    return build_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        user_action=exc.user_action,
        details=exc.details
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Simplifies standard HTTPExceptions into friendly user responses."""
    code_map = {
        400: ("BAD_REQUEST", "The submitted request could not be processed due to invalid parameters.", "Check the provided inputs and try again."),
        401: ("UNAUTHORIZED", "Your session has expired or your credentials are invalid.", "Please sign in with your email and password."),
        403: ("FORBIDDEN", "You do not have permission to perform this store management action.", "Contact your store supervisor or administrator for elevated access."),
        404: ("NOT_FOUND", "The requested store, transaction, or product record could not be found.", "Verify the identifier or search query."),
        422: ("VALIDATION_ERROR", "One or more submitted values are formatted incorrectly.", "Please check the required fields and numeric ranges."),
        429: ("TOO_MANY_REQUESTS", "Too many requests submitted in a short period.", "Please wait a moment before trying again."),
        500: ("SERVER_ERROR", "An unexpected operational error occurred on the store server.", "Our technical team has been notified. Please retry in a few moments.")
    }
    
    code, default_msg, default_action = code_map.get(
        exc.status_code,
        ("HTTP_ERROR", str(exc.detail), "Please verify your request.")
    )
    
    message = str(exc.detail) if exc.detail and exc.detail != "" else default_msg
    
    # Check if there is an in-store hub error code in the message (e.g. E312)
    for hub_code, trans in HUB_ERROR_TRANSLATIONS.items():
        if hub_code in message:
            message = f"{trans['title']} ({hub_code}): {trans['message']}"
            default_action = trans['user_action']
            code = f"STORE_HUB_{hub_code}"
            break
            
    return build_error_response(
        status_code=exc.status_code,
        code=code,
        message=message,
        user_action=default_action
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Translates complex Pydantic validation errors into clean plain English."""
    friendly_errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []) if loc != "body")
        msg = err.get("msg", "Invalid value")
        friendly_errors.append(f"Field '{field}': {msg}")
    
    summary_msg = "Invalid data submitted: " + "; ".join(friendly_errors) if friendly_errors else "Submitted data failed validation checks."
    
    return build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="FORM_VALIDATION_FAILED",
        message=summary_msg,
        user_action="Please review the highlighted fields in the form and provide valid inputs.",
        details=exc.errors()
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches unhandled server exceptions and returns a clean, safe message."""
    return build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected system error occurred while processing this store request.",
        user_action="Please refresh the page. If the issue persists, contact Brightleaf Store IT Support.",
        details=str(exc)
    )
