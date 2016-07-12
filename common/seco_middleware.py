import json
import logging
import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError

from django.conf import settings

log = logging.getLogger("common.seco_middleware")

IDAM_ERROR_CODES = {
    (204,):
        {'error_info': {'success': False,
                       'error': 'no_content',
                       'value': "Sorry your information could \
                                 not be fetched right now. \
                                 Please try again after \
                                 sometime."
                       }
        },
    (400,):
        {'error_info': {'success': False,
                        'error': 'bad_request',
                        'value': "Sorry you could not be \
                                  authenticated. Please check \
                                  your credentials. Thank you!"
                       }
        },
    (403,):
        {'error_info': {'success': False,
                        'error': 'permission_error',
                        'value': "Sorry you do not have \
                                  permission to access this \
                                  service now. Thank you!"
                       }
        },
    (404,):
        {'error_info': {'success': False,
                        'error': 'page_not_found',
                        'value': "Page Not Found."
                       }
        },
    (500, 501, 503, 504, 505,):
        {'error_info': {'success': False,
                        'error': 'server_error',
                        'value': "We are facing some network \
                                  related issue. Please try \
                                  to login after sometime. \
                                  Thank you!"
                       }
        }
}

SERVICE_END_POINT_URL = {
                            'verify': 'user/unpw/verify',
                            'session_get': 'session/details/get'
                        }


class SecoApiMiddleware(object):
    IDAM_ERROR_CODES = IDAM_ERROR_CODES
    SERVICE_END_POINT_URL = SERVICE_END_POINT_URL
    BASE_SECO_API_URL = settings.SECO_AUTHENTICATION.get('SECO_BASE_URL', None)
    X_API_KEY = settings.SECO_AUTHENTICATION.get('X_API_KEY', None)

    @staticmethod
    def get_error_info(code):
        """
        Returns error info for a particular status
        code(except 200) from REST call.
        """
        try:
            return [value for key, value in
                    SecoApiMiddleware.IDAM_ERROR_CODES.iteritems()
                    if code in key][0]
        except:
            log.debug("Undefined SECO REST api status code(%s)." % code)
            return {'error_info': {'success': False,
                                   'value': "Currently could \
                                             not process your \
                                             request."
                                  }
                   }

    @staticmethod
    def get_seco_api_url(service):
        """
        Returns absolute SECO api url for a particular service.
        """
        return "{}/{}".format(SecoApiMiddleware.BASE_SECO_API_URL,
        (SecoApiMiddleware.SERVICE_END_POINT_URL.get(service, None)))

    @staticmethod
    def verify(form_data, service='verify'):
        """
        SECO api verify method.
        Returns json response that contains sso-token on success.
        """
        url = SecoApiMiddleware.get_seco_api_url(service)
        headers = {"X-API-Key": SecoApiMiddleware.X_API_KEY,
                   "Content-Type": "application/json"
                  }
        data = {"identifier": form_data['identifier'],
                "password": form_data['password'],
                "upgradeAuth": "Y"
               }
        return SecoApiMiddleware.get_api_response(url, data, headers)

    @staticmethod
    def session_get(token, service='session_get'):
        """
        SECO api session set method.
        Retuns particular user's details based
        on the value set on data param(T/F).
        """
        url = SecoApiMiddleware.get_seco_api_url(service)
        headers = {"X-API-Key": SecoApiMiddleware.X_API_KEY,
                   "Content-Type": "application/json",
                   "sso-token": "%s" % token
                  }
        data = {
                "includeUserDetails": "T",
                "includeProfileDetails": "T",
                "includeEntitlements": "T"
            }
        return SecoApiMiddleware.get_api_response(url, data, headers)

    @staticmethod
    def get_api_response(url, data, headers, timeoutValue=20):
        """
        Generic method that calls SECO api and returns
        response to calling function.
        """
        try:
            response = requests.post(url, data=json.dumps(data),
                                     headers=headers,
                                     timeout=timeoutValue)
            status_code = response.status_code
        except HTTPError:
            status_code = 504
            log.error("HTTPError exception while \
                       getting response from url : " + url)
        except Timeout:
            status_code = 504
            log.error("Timeout exception while getting \
                       response from url : " + url)
        except ConnectionError:
            status_code = 504
            log.error("ConnectionError exception while getting \
                       response from url : " + url)
        log.debug("SECO REST api response status code: %s" % status_code)
        if status_code == 200:  # success request
            return json.loads(response.text), status_code
        log.error("SECO REST api call failed. So returning error details.")
        return SecoApiMiddleware.get_error_info(status_code), status_code
