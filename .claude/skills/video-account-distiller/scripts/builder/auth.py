import base64
import json

from dy_apis.douyin_api import DouyinAPI
from utils.dy_util import generate_fake_webid, generate_msToken, trans_cookies


class DouyinAuth:
    def __init__(self):
        self.cookie = None
        self.cookie_str = None
        self.private_key = None
        self.ticket = None
        self.ts_sign = None
        self.client_cert = None
        self.ree_public_key = None
        self.uid = None
        self.msToken = None

    def perepare_auth(self, cookieStr: str, web_protect_: str = "", keys_: str = ""):
        if not cookieStr:
            raise ValueError("DY_COOKIES is empty. Please login Douyin first.")
        self.cookie = trans_cookies(cookieStr)
        self.cookie = {
            k: v for k, v in self.cookie.items()
            if _is_header_safe(k) and _is_header_safe(v)
        }
        if "s_v_web_id" not in self.cookie:
            self.cookie["s_v_web_id"] = generate_fake_webid()
        self.cookie_str = cookieStr
        self.msToken = self.cookie["msToken"] if "msToken" in self.cookie else generate_msToken()
        self.cookie["msToken"] = self.msToken
        self.cookie_str = "; ".join([f"{k}={v}" for k, v in self.cookie.items()])
        if web_protect_ != "":
            web_protect_ = json.loads(json.loads(web_protect_)['data'])
            self.ticket = web_protect_['ticket']
            self.ts_sign = web_protect_['ts_sign']
            self.client_cert = web_protect_['client_cert']
        if keys_ != "":
            keys_ = json.loads(json.loads(keys_)['data'])
            self.private_key = keys_['ec_privateKey']
            self.ree_public_key = base64.b64encode(self.private_key.encode()).decode()


    def get_uid(self):
        if self.uid is None:
            self.uid = DouyinAPI.get_my_uid(self)
        return self.uid


def _is_header_safe(value):
    try:
        str(value).encode("latin-1")
        return True
    except UnicodeEncodeError:
        return False
