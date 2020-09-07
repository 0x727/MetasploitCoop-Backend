from requests.auth import AuthBase


class BearerTokenAuth(AuthBase):
    def __init__(self, token: str):
        self.token = token
    
    def __call__(self, r):
        r.headers['accept'] = 'application/json'
        r.headers['Authorization'] = f'Bearer {self.token}'
        return r