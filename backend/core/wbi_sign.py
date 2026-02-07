import hashlib
import time
import urllib.parse

class BilibiliSign:
    """WBI parameter signing for Bilibili APIs."""
    
    # Standard 64-element shuffle table for Bilibili WBI
    MIXIN_KEY_ENC_TAB = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
        61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
        36, 20, 34, 44, 52
    ]

    def __init__(self, img_key: str, sub_key: str):
        if not img_key or not sub_key:
            # Fallback or error handling
            self.mixin_key = ""
            return
        raw = img_key + sub_key
        self.mixin_key = "".join(raw[i] for i in self.MIXIN_KEY_ENC_TAB)[:32]

    def sign(self, params: dict) -> dict:
        """
        Signs the given parameters with a WBI signature.
        Adds 'wts' and 'w_rid' to the dictionary.
        """
        # 1. Add timestamp
        params["wts"] = int(time.time())
        
        # 2. Sort parameters by key
        sorted_params = dict(sorted(params.items()))
        
        # 3. Filter special characters from values (B站 WBI requirement)
        def _filter_value(v):
            s = str(v)
            for ch in "!'()*":
                s = s.replace(ch, "")
            return s
        sorted_params = {k: _filter_value(v) for k, v in sorted_params.items()}
        query = urllib.parse.urlencode(sorted_params)
        
        # 4. Concatenate with mixin_key and MD5
        sign_str = query + self.mixin_key
        params["w_rid"] = hashlib.md5(sign_str.encode()).hexdigest()
        
        return params

def get_mixin_key(img_key: str, sub_key: str) -> str:
    """Helper to get mixin key directly."""
    raw = img_key + sub_key
    return "".join(raw[i] for i in BilibiliSign.MIXIN_KEY_ENC_TAB)[:32]
