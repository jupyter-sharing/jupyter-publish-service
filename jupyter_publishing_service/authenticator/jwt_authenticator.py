import jwcrypto.jws as jws
import jwcrypto.jwt as jwt
from httpx import AsyncClient, Client, create_ssl_context
from jwcrypto.common import base64url_decode, json_decode
from jwcrypto.jwk import JWK
from traitlets import Dict
from traitlets.config import LoggingConfigurable

from jupyter_publishing_service import constants
from jupyter_publishing_service.authenticator.abc import AuthenticatorABC
from jupyter_publishing_service.traits import UnicodeFromEnv


class JWTAuthenticator(LoggingConfigurable):
    _alg = "RS256"
    public_key_url = UnicodeFromEnv(
        name=constants.JWKS_URI,
        help="JWK URI of keys used for signing the JWT e.g https://www.googleapis.com/oauth2/v3/certs",
        default_value="",
        allow_none=False,
    ).tag(config=True)

    ssl_cert_file = UnicodeFromEnv(name=constants.SSL_CERT_FILE, allow_none=True).tag(config=True)

    public_keys = Dict(
        help="Public keys for decoding the JWT tokens in each request. "
        "If not given, the authenticator will make a separate GET request to "
        "the `key_url` to retrieve these keys. Kid is used as key, public key as value",
        allow_none=True,
    ).tag(config=True)

    async def fetch_public_keys(self):
        context = create_ssl_context(verify=self.ssl_cert_file)
        return await AsyncClient(verify=context).get(self.public_key_url)

    async def get_public_key_by_kid(self, token: str) -> JWK:
        """Fetch public keys for authentication of the JWT.
        If public keys are set by configuration (likely only used
        in local mode), don't fetch the keys here; just return
        them pre-configured list of public
        """
        headers = json_decode(base64url_decode(token.split(".")[0]))
        if headers["kid"] is None:
            raise jws.InvalidJWSObject(message="missing kid in token headers")
        kid = headers["kid"]
        if not self.public_keys or kid not in self.public_keys:
            new_public_keys = {}
            r = await self.fetch_public_keys()
            response = json_decode(r.content)
            if r.status_code == 200:
                publickeys = response.pop("keys", [])
                for public_key in publickeys:
                    if public_key["alg"] == self._alg:
                        new_public_keys[public_key["kid"]] = JWK(**public_key)
                self.public_keys = new_public_keys
            else:
                self.log.error("failed to retrieve key to validate jwt token")
                r.raise_for_status()
        if kid in self.public_keys:
            return self.public_keys[kid]
        else:
            self.log.error("failed to get public key from ias with required kid")
            raise jws.InvalidJWSObject(message="token's kid is invalid")

    async def get_expiration(self, jwt_token: str) -> int:
        public_key = await self.get_public_key_by_kid(jwt_token)
        try:
            decoded_jwt = jwt.JWT(
                jwt=jwt_token,
                key=public_key,
                check_claims={"exp": None},
            )
            decoded_claims = json_decode(decoded_jwt.claims)
            return decoded_claims["exp"]
        except jws.InvalidJWSSignature as e:
            self.log.error(f"failed to decode jwt using public key, public_key={public_key}, e={e}")
            return -1

    @staticmethod
    def get_current_user(jwt_token: str, public_key: JWK) -> dict:
        decoded_jwt = jwt.JWT(
            jwt=jwt_token,
            key=public_key,
            check_claims={
                "exp": None,
            },
        )
        return json_decode(decoded_jwt.claims)

    async def authenticate(self, credentials: dict) -> dict:
        token = credentials["token"]
        public_key = await self.get_public_key_by_kid(token)
        try:
            return self.get_current_user(token, public_key)
        except jws.InvalidJWSSignature as e:
            self.log.error(f"invalid public key: error {e}")
        except jwt.JWTMissingClaim as e:
            self.log.error(f"missingClaim: {e}")
        except jwt.JWTInvalidClaimValue as e:
            self.log.error(f"one or more claims are invalid: {e}")
        except jwt.JWTExpired as e:
            self.log.error(f"token is expired: {e}")
        except jws.InvalidJWSObject as e:
            self.log.error(f"invalid token: {e}")
        except Exception as e:
            self.log.error(f"token validation failed: {e}")
        return {}


AuthenticatorABC.register(JWTAuthenticator)
