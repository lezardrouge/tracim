# coding: utf-8
import typing

from pyramid.response import Response
from tracim_backend.lib.calendar.authorization import DavAuthorization
from tracim_backend.lib.calendar.determiner import CaldavAuthorizationDeterminer

from tracim_backend.lib.proxy.proxy import Proxy

from sqlalchemy.orm import Session

from tracim_backend.lib.utils.authorization import check_user_calendar_authorization, \
    can_modify_workspace
from tracim_backend.lib.utils.request import TracimContext
from tracim_backend.models import User
from tracim_backend.models.data import Workspace

if typing.TYPE_CHECKING:
    from tracim_backend import CFG, TracimRequest

class RadicaleApi(object):
    def __init__(
        self,
        session: Session,
        current_user: typing.Optional[User],
        config: 'CFG',
        proxy: Proxy,
        authorization: CaldavAuthorizationDeterminer,
    ):
        self._user = current_user
        self._session = session
        self._config = config
        self._proxy = proxy
        self._authorization = authorization

    def get_remote_user_calendar_response(self, request: 'TracimRequest', user: User) -> Response:
        return self._proxy.get_response_for_request(
            request,
            # FIXME BS 2018-12-17: /radicale/ must be set because
            # raidcale will respond url with this path in PROPFIND requests
            'user/{}.ics'.format(user.user_id)
        )

    def get_remote_user_calendars_response(self, request: 'TracimRequest') -> Response:
        return self._proxy.get_response_for_request(
            request,
            # FIXME BS 2018-12-17: /radicale/ must be set because
            # raidcale will respond url with this path in PROPFIND requests
            'user/',
        )

    def get_remote_workspace_calendar_response(
        self, request: 'TracimRequest', workspace: Workspace,
    ) -> Response:
        return self._proxy.get_response_for_request(
            request,
            # FIXME BS 2018-12-17: /radicale/ must be set because
            # raidcale will respond url with this path in PROPFIND requests
            'workspace/{}.ics'.format(workspace.workspace_id),
        )

    def get_remote_workspace_calendars_response(
        self, request: 'TracimRequest', workspace: Workspace,
    ) -> Response:
        return self._proxy.get_response_for_request(
            request,
            # FIXME BS 2018-12-17: /radicale/ must be set because
            # raidcale will respond url with this path in PROPFIND requests
            'workspace/',
        )
