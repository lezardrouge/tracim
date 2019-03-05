# coding: utf-8
from enum import Enum

from hapic.error.marshmallow import MarshmallowDefaultErrorBuilder
from hapic.ext.pyramid import PyramidContext
from pyramid.response import Response

def add_special_header_for_caldav(config):
    pass

class DavAuthorization(Enum):
    READ = 'r'
    WRITE = 'w'


# class TracimPyramidContext(PyramidContext):
#     def get_response(
#         self, response: str, http_code: int, mimetype: str = "application/json"
#     ) -> Response:
#         response = super().get_response(response, http_code, mimetype)
#
#         # FIXME BS 2018-12-10: This is a hack to be able to add WWW-Authenticate
#         try:
#             if response.json['code'] == error.:
#                 # TODO BS 2018-12-10: Traduce realm
#                 response.headerlist.append(('WWW-Authenticate', 'Basic realm="Tracim credentials"'))
#                 return response
#         except:
#             pass
#         return response


# class RadicaleProxyErrorBuilder(MarshmallowDefaultErrorBuilder):
#     def build_from_exception(
#         self, exception: Exception, include_traceback: bool = False
#     ) -> dict:
#         error_content = super().build_from_exception(exception)
#         # FIXME BS 2018-12-10: This is a hack to be able to add WWW-Authenticate
#         error_content['code'] = 4422
#         return error_content
