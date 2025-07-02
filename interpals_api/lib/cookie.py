class Cookie(dict):
    """
    A class that manages HTTP cookies.
    """

    def as_string(self):
        """
        Represents saves cookie values as a string for HTTP header.
        """
        return "; ".join(
            "{}={}".format(key, value) for key, value in self.items()
        )

    def __repr__(self):
        return self.as_string()

    # @classmethod
    # def parse_set_cookie(cls, set_cookie):
    #     """
    #     Extracts key and value of a cookie from Set-Cookie header of an HTTP response.
    #     """
    #     key, value = set_cookie[:set_cookie.find(';')].split('=')
    #     key = key.strip()
    #     value = value.strip()
    #     return key, value

    # @classmethod
    # def from_response_headers(cls, headers):
    #     """
    #     Creates cookie instance from HTTP response headers.
    #     """
    #     obj = cls()
    #     for key, value in headers.items():
    #         if key.lower() == "set-cookie":
    #             for val in value.split("HttpOnly,"):
    #                 cookie_key, cookie_value = cls.parse_set_cookie(val)
    #                 obj[cookie_key] = cookie_value
        return obj
    @classmethod
    def parse_set_cookie(cls, set_cookie):
        """
        Extracts key and value of a cookie from Set-Cookie header of an HTTP response.
        """
        # Extract just key and value from beginning of cookie string up to first semicolon
        parts = set_cookie.split(';', 1)[0].split('=', 1)
        if len(parts) != 2:
            return None, None
        return parts[0].strip(), parts[1].strip()

    @classmethod
    def from_response_headers(cls, headers):
        """
        Creates cookie instance from HTTP response headers.
        Hardcoded to look for specific cookies: interpals_sessid, __ubic1, and csrf_cookieV2
        """
        obj = cls()
        
        # If it's a string, process it directly
        if isinstance(headers, str):
            cookie_str = headers
            
            # Extract interpals_sessid
            if 'interpals_sessid=' in cookie_str:
                start = cookie_str.find('interpals_sessid=') + len('interpals_sessid=')
                end = cookie_str.find(';', start)
                if end != -1:
                    obj['interpals_sessid'] = cookie_str[start:end].strip()
                else:
                    obj['interpals_sessid'] = cookie_str[start:].strip()
            
            # Extract __ubic1
            if '__ubic1=' in cookie_str:
                start = cookie_str.find('__ubic1=') + len('__ubic1=')
                end = cookie_str.find(';', start)
                if end != -1:
                    obj['__ubic1'] = cookie_str[start:end].strip()
                else:
                    obj['__ubic1'] = cookie_str[start:].strip()
            
            # Extract csrf_cookieV2
            if 'csrf_cookieV2=' in cookie_str:
                start = cookie_str.find('csrf_cookieV2=') + len('csrf_cookieV2=')
                end = cookie_str.find(';', start)
                if end != -1:
                    obj['csrf_cookieV2'] = cookie_str[start:end].strip()
                else:
                    obj['csrf_cookieV2'] = cookie_str[start:].strip()
        
        # Process headers dictionary
        else:
            for key, value in headers.items():
                if key.lower() == "set-cookie":
                    if 'interpals_sessid=' in value:
                        start = value.find('interpals_sessid=') + len('interpals_sessid=')
                        end = value.find(';', start)
                        if end != -1:
                            obj['interpals_sessid'] = value[start:end].strip()
                        else:
                            obj['interpals_sessid'] = value[start:].strip()
                    
                    if '__ubic1=' in value:
                        start = value.find('__ubic1=') + len('__ubic1=')
                        end = value.find(';', start)
                        if end != -1:
                            obj['__ubic1'] = value[start:end].strip()
                        else:
                            obj['__ubic1'] = value[start:].strip()
                    
                    if 'csrf_cookieV2=' in value:
                        start = value.find('csrf_cookieV2=') + len('csrf_cookieV2=')
                        end = value.find(';', start)
                        if end != -1:
                            obj['csrf_cookieV2'] = value[start:end].strip()
                        else:
                            obj['csrf_cookieV2'] = value[start:].strip()
        
        return obj
