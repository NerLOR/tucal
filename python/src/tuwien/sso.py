
from typing import Optional
import requests
import re

import tucal

SSO_DOMAIN = 'idp.zid.tuwien.ac.at'
SSO_URL = f'https://{SSO_DOMAIN}'

INPUT_AUTH_STATE = re.compile(r'<input type="hidden" name="AuthState" value="([^"]*)" */?>')
INPUT_STATE_ID = re.compile(r'<input type="hidden" name="StateId" value="([^"]*)" */?>')
FORM_ACTION = re.compile(r'action="([^"]*)"')
INPUT_SAML_RES = re.compile(r'<input type="hidden" name="SAMLResponse" value="([^"]*)" */?>')
INPUT_RELAY_STATE = re.compile(r'<input type="hidden" name="RelayState" value="([^"]*)" */?>')


class Session:
    _session: requests.Session
    _username: Optional[str]
    _password: Optional[str]
    _totp: Optional[str]

    def __init__(self, session: requests.Session = None):
        self._username = None
        self._password = None
        self._session = session or requests.Session()

    def credentials(self, username: str, password: str, totp: str = None):
        self._username = username
        self._password = password
        self._totp = totp

    def login(self, url: str = 'https://login.tuwien.ac.at/') -> bool:
        r = self._session.get(url)
        if r.status_code != 200:
            raise tucal.LoginError(r.reason)
        elif not r.url.startswith(SSO_URL):
            return True

        if '<title>TU Wien Login</title>' in r.text:
            auth_state = INPUT_AUTH_STATE.search(r.text).group(1)
            r = self._session.post(f'{SSO_URL}/simplesaml/module.php/core/loginuserpass.php', {
                'username': self._username or '',
                'password': self._password or '',
                'totp': self._totp or '',
                'AuthState': auth_state,
            })

            if r.status_code != 200:
                raise tucal.LoginError(r.reason)
            elif '<h3>Benutzername oder Passwort falsch.</h3>' in r.text:
                raise tucal.InvalidCredentialsError('invalid credentials')

        if '<title>Hohes Passwortalter</title>' in r.text:
            state_id = INPUT_STATE_ID.search(r.text).group(1)
            r = self._session.post(f'{SSO_URL}/simplesaml/module.php/oldPW/confirmOldPW.php', {
                'yes': '',
                'StateId': state_id,
            })

        if '<title>Zustimmung zur Weitergabe persönlicher Daten</title>' in r.text:
            state_id = INPUT_STATE_ID.search(r.text).group(1)
            r = self._session.post(f'{SSO_URL}/simplesaml/module.php/consent/getconsent.php', {
                'yes': '',
                'saveconsent': '1',
                'StateId': state_id,
            })

        action = FORM_ACTION.search(r.text).group(1)
        saml_res = INPUT_SAML_RES.search(r.text).group(1)
        relay_state = INPUT_RELAY_STATE.search(r.text).group(1)

        r = self._session.post(action, {
            'SAMLResponse': saml_res,
            'RelayState': relay_state,
        })

        if r.status_code != 200:
            raise tucal.LoginError(r.reason)

        return True

    @property
    def session(self) -> requests.Session:
        return self._session
