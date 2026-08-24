"""Small middleware utilities for the OCMO API."""


class ResolveCacheHeaderMiddleware:
    """Add ``X-Ocmo-Resolve-Cache: hit|cast|miss`` to resolve responses.

    ``ResolutionManager.resolve()`` sets ``request._resolve_cache_status``
    after processing a resolve request.  Possible values:

    ``hit``
        All items were served from the Layer 2 artifact cache — no pipeline
        run and no cast was performed.
    ``cast``
        All items were served from the Layer 1 resolution cache — no pipeline
        run, but casting and artifact storage were performed.
    ``miss``
        At least one item required a full pipeline run.

    This middleware reads that attribute and adds the header to the response
    so callers (tests, operators) can distinguish the three tiers without
    parsing the response body.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        status = getattr(request, "_resolve_cache_status", None)
        if status is not None:
            response["X-Ocmo-Resolve-Cache"] = status
        return response
