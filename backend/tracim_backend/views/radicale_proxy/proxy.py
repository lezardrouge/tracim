# coding: utf-8
import marshmallow as marshmallow
from hapic import HapicData
from pyramid.config import Configurator
from pyramid.response import Response
from tracim_backend.extensions import hapic
from tracim_backend.exceptions import CaldavNotAuthorized, InsufficientUserRoleInWorkspace
from tracim_backend.exceptions import NotAuthenticated
from tracim_backend.lib.calendar.radicale import RadicaleApi
from tracim_backend.lib.calendar.determiner import CaldavAuthorizationDeterminer
from tracim_backend.lib.proxy.proxy import Proxy
from tracim_backend.lib.utils.authorization import check_right, \
    is_user, is_reader, can_access_workspace_calendar, can_access_user_calendar, \
    can_access_to_calendar_list
from tracim_backend.lib.utils.request import TracimRequest
from tracim_backend.views.controllers import Controller


# FIXME BS 2018-12-06: Move
class UserCalendarPath(marshmallow.Schema):
    user_id = marshmallow.fields.String(required=True)


# FIXME BS 2018-12-06: Move
class WorkspaceCalendarPath(marshmallow.Schema):
    workspace_id = marshmallow.fields.String(required=True)


class RadicaleProxyController(Controller):
    def __init__(self):
        self._authorization = CaldavAuthorizationDeterminer()
        from tracim_backend import CALENDAR_BASE_URL
        self._proxy = Proxy(
            # FIXME BS 2018-11-27: from config
            base_address_host='http://127.0.0.1:4321',
            base_address_path=CALENDAR_BASE_URL,
        )

    @hapic.with_api_doc(disable_doc=True)
    @check_right(can_access_user_calendar)
    @hapic.input_path(UserCalendarPath())
    def radicale_proxy__user(
        self, context, request: TracimRequest, hapic_data: HapicData,
    ) -> Response:
        radicale_api = RadicaleApi(
            config=request.registry.settings['CFG'],
            current_user=request.current_user,
            session=request.dbsession,
            proxy=self._proxy,
            authorization=self._authorization,
        )

        radicale_response = radicale_api.get_remote_user_calendar_response(
            request,
            request.candidate_user
        )
        return radicale_response

    @hapic.with_api_doc(disable_doc=True)
    # @hapic.handle_exception(
    #     NotAuthenticated,
    #     http_code=401,
    #     error_builder=RadicaleProxyErrorBuilder(),
    # )
    @check_right(can_access_to_calendar_list)
    def radicale_proxy__users(
        self, context, request: TracimRequest,
    ) -> Response:
        radicale_api = RadicaleApi(
            config=request.registry.settings['CFG'],
            current_user=request.current_user,
            session=request.dbsession,
            proxy=self._proxy,
            authorization=self._authorization,
        )

        radicale_response = radicale_api.get_remote_user_calendars_response(
            request,
        )
        return radicale_response

    @hapic.with_api_doc(disable_doc=True)
    # @hapic.handle_exception(
    #     NotAuthenticated,
    #     http_code=401,
    #     error_builder=RadicaleProxyErrorBuilder(),
    # )
    # @hapic.handle_exception(CaldavNotAuthorized, http_code=403)
    # # FIXME BS 2018-12-10: Check it is the raise exception in cas of not workspace write auth
    # @hapic.handle_exception(InsufficientUserRoleInWorkspace, http_code=403)

    @check_right(can_access_workspace_calendar)
    @hapic.input_path(WorkspaceCalendarPath())
    def radicale_proxy__workspace(
        self, context, request: TracimRequest, hapic_data: HapicData,
    ) -> Response:
        radicale_api = RadicaleApi(
            config=request.registry.settings['CFG'],
            current_user=request.current_user,
            session=request.dbsession,
            proxy=self._proxy,
            authorization=self._authorization,
        )

        radicale_response = radicale_api.get_remote_workspace_calendar_response(
            request,
            workspace=request.candidate_workspace,
        )
        return radicale_response

    @hapic.with_api_doc(disable_doc=True)
    # @hapic.handle_exception(
    #     NotAuthenticated,
    #     http_code=401,
    #     error_builder=RadicaleProxyErrorBuilder(),
    # )
    # @hapic.handle_exception(CaldavNotAuthorized, http_code=403)
    @check_right(can_access_to_calendar_list)
    def radicale_proxy__workspaces(
        self, context, request: TracimRequest,
    ) -> Response:
        radicale_api = RadicaleApi(
            config=request.registry.settings['CFG'],
            current_user=request.current_user,
            session=request.dbsession,
            proxy=self._proxy,
            authorization=self._authorization,
        )

        radicale_response = radicale_api.get_remote_workspace_calendars_response(
            request,
            workspace=request.current_workspace,
        )
        return radicale_response

    def bind(self, configurator: Configurator) -> None:
        """
        Create all routes and views using pyramid configurator
        for this controller
        """
        # Radicale user calendar
        configurator.add_route(
            'radicale_proxy__user',
            '/user/{user_id:[0-9]+}.ics/',
        )
        configurator.add_view(
            self.radicale_proxy__user,
            route_name='radicale_proxy__user',
        )

        configurator.add_route(
            'radicale_proxy__users',
            '/user/',
        )
        configurator.add_view(
            self.radicale_proxy__users,
            route_name='radicale_proxy__users',
        )

        configurator.add_route(
            'radicale_proxy__user_x',
            '/user/{user_id:[0-9]+}.ics/{what_is_it_id:[a-zA-Z0-9]+}.ics/',
        )
        configurator.add_view(
            self.radicale_proxy__user,
            route_name='radicale_proxy__user_x',
        )

        # Radicale workspace calendar
        configurator.add_route(
            'radicale_proxy__workspace',
            '/workspace/{workspace_id:[0-9]+}.ics/',
        )
        configurator.add_view(
            self.radicale_proxy__workspace,
            route_name='radicale_proxy__workspace',
        )

        configurator.add_route(
            'radicale_proxy__workspace_x',
            '/workspace/{workspace_id:[0-9]+}.ics/{what_is_it_id:[a-zA-Z0-9]+}.ics/',
        )
        configurator.add_view(
            self.radicale_proxy__workspace,
            route_name='radicale_proxy__workspace_x',
        )

        configurator.add_route(
            'radicale_proxy__workspaces',
            '/workspace/',
        )
        configurator.add_view(
            self.radicale_proxy__workspaces,
            route_name='radicale_proxy__workspaces',
        )
