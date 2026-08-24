from ._common import *


class TreeResolverOpsMixin:
    @audit("resolver", operation=OP_ROTATE_TOKEN, subresource_type="token")
    @require_permissions("resolver:write")
    def rotate_resolver_token(self, token_num: int):
        """Rotate token1 or token2 for a resolver."""
        self._ensure_writable()
        self.get_or_raise(["resolver"])
        if token_num not in [1, 2]:
            raise ValidationError(f"Token number must be 1 or 2, got {token_num}")
        enrich_audit(subresource=str(token_num))
        plaintext = generate_resolver_token()
        ResolverTokenManager(plaintext=plaintext).assign_to(self.item, token_num)
        if token_num == 1:
            self.item.token1_last_used = None
        else:
            self.item.token2_last_used = None
        self.item.save()
        return ResolverTokenRotationResponseSchema(token_number=token_num, token=plaintext)
