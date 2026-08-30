import { UserManager, WebStorageStateStore } from "oidc-client-ts";
import { fetchVersion } from "../api/client";
import type { PublicOidcAuth } from "../api/types";
import { env } from "../env";
import { useHealthStore } from "../store/health";

let userManager: UserManager | null = null;
let initPromise: Promise<UserManager> | null = null;

function createUserManager(oidc: PublicOidcAuth): UserManager {
  return new UserManager({
    authority: oidc.issuer,
    client_id: oidc.client_id,
    redirect_uri: env.oidcRedirectUri,
    silent_redirect_uri: env.oidcSilentRedirectUri,
    post_logout_redirect_uri: env.oidcPostLogoutRedirectUri,
    scope: oidc.scopes,
    response_type: "code",
    automaticSilentRenew: true,
    userStore: new WebStorageStateStore({ store: window.localStorage }),
    loadUserInfo: true,
  });
}

/** Load OIDC client settings from `/api/version` and construct the UserManager. */
export async function initUserManager(): Promise<UserManager> {
  if (userManager) return userManager;

  if (!initPromise) {
    initPromise = fetchVersion()
      .then((version) => {
        useHealthStore.getState().applyVersionResponse(version);
        userManager = createUserManager(version.auth.oidc);
        return userManager;
      })
      .catch((err) => {
        initPromise = null;
        throw err;
      });
  }

  return initPromise;
}

export function getUserManager(): UserManager {
  if (!userManager) {
    throw new Error("OIDC is not initialized — call initUserManager() first");
  }
  return userManager;
}
