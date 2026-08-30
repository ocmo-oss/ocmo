import { useEffect } from "react";
import { initUserManager } from "../auth/oidc";

/** OIDC silent-renew iframe target — must call signinSilentCallback, not the full app shell. */
export function SilentCallbackPage() {
  useEffect(() => {
    void initUserManager().then((um) => um.signinSilentCallback());
  }, []);

  return null;
}
