# -*- coding: utf-8 -*-
# INFO - G.M -17-05-2018 - CORS support
# original code from https://gist.github.com/mmerickel/1afaf64154b335b596e4
# see also
# here : https://groups.google.com/forum/#!topic/pylons-discuss/2Sw4OkOnZcE
import typing

from pyramid.events import NewResponse
from tracim_backend.lib.calendar.determiner import CALDAV_WRITE_METHODS, CALDAV_READ_METHODS


def add_cors_support(config):
    # INFO - G.M - 17-05-2018 - CORS Preflight stuff (special requests)
    config.add_directive(
        'add_cors_preflight_handler',
        add_cors_preflight_handler
    )
    config.add_route_predicate('cors_preflight', CorsPreflightPredicate)

    # INFO - G.M - 17-05-2018 CORS Headers for all responses
    config.add_subscriber(add_cors_to_response, NewResponse)


class CorsPreflightPredicate(object):
    def __init__(self, val, config):
        self.val = val

    def text(self):
        return 'cors_preflight = %s' % bool(self.val)

    phash = text

    def __call__(self, context, request):
        if not self.val:
            return False
        return (
            request.method == 'OPTIONS' and
            'Origin' in request.headers and
            'Access-Control-Request-Method' in request.headers
        )


def add_cors_preflight_handler(config):
    # INFO - G.M - 17-05-2018 - Add route for CORS preflight
    # see https://developer.mozilla.org/en-US/docs/Glossary/Preflight_request
    # for more info about preflight

    config.add_route(
        'cors-options-preflight', '/{catch_all:.*}',
        cors_preflight=True,
    )
    config.add_view(
        cors_options_view,
        route_name='cors-options-preflight',
    )


def cors_options_view(context, request):
    response = request.response

    if 'Access-Control-Request-Headers' in request.headers:
        response.headers['Access-Control-Allow-Methods'] = (
            ','.join(
                ['OPTIONS,HEAD,GET,POST,PUT,DELETE'] +
                CALDAV_WRITE_METHODS +
                CALDAV_READ_METHODS
            )
        )

    # FIXME BS 2018-12-17
    app_config = request.registry.settings['CFG']
    if 'Origin' in request.headers and request.headers['Origin'] in app_config.CORS_ALLOWED_ORIGIN:
        response.headers['Access-Control-Allow-Origin'] = request.headers['Origin']

    response.headers['Access-Control-Allow-Headers'] = (
        'Content-Type,Date,Content-Length,Authorization,X-Request-ID,'
        'User-Agent,Depth,If-match,If-None-Match,Lock-Token,Timeout,'
        'Destination,Overwrite,X-client,X-Requested-With,Request,Authorization,'
        'Prefer'
    )
    response.headers['Access-Control-Expose-Headers'] = (
        'Content-Type,Date,Content-Length,Authorization,X-Request-ID,Etag'
    )
    return response


def add_cors_to_response(event):
    # INFO - G.M - 17-05-2018 - Add some CORS headers to all requests
    request = event.request
    response = event.response
    app_config = request.registry.settings['CFG']
    if 'Origin' in request.headers and request.headers['Origin'] in app_config.CORS_ALLOWED_ORIGIN:  # nopep8
        headers_to_add = get_cors_headers_to_add(origin=request.headers['Origin'])
        response.headers.update(headers_to_add)


def get_cors_headers_to_add(origin: str) -> typing.Dict[str, str]:
    return {
        'Access-Control-Expose-Headers': (
            'Content-Type,Date,Content-Length,Authorization,X-Request-ID,Etag'
        ),
        'Access-Control-Allow-Headers': (
            'Content-Type,Date,Content-Length,Authorization,X-Request-ID,'
            'User-Agent,Depth,If-match,If-None-Match,Lock-Token,Timeout,'
            'Destination,Overwrite,X-client,X-Requested-With,Request,'
            'Prefer'
        ),
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Credentials': 'true',
        'Vary': 'Origin',
    }
