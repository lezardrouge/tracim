# -*- coding: utf-8 -*-
"""
Tests for /api/v2/workspaces subpath endpoints.
"""
from depot.io.utils import FileIntent
import transaction

from tracim_backend.app_models.contents import content_type_list
from tracim_backend.error import ErrorCode
from tracim_backend.extensions import app_list
from tracim_backend.fixtures.content import Content as ContentFixtures
from tracim_backend.fixtures.users_and_groups import Base as BaseFixture
from tracim_backend.lib.core.application import ApplicationApi
from tracim_backend.lib.core.content import ContentApi
from tracim_backend.lib.core.group import GroupApi
from tracim_backend.lib.core.user import UserApi
from tracim_backend.lib.core.userworkspace import RoleApi
from tracim_backend.lib.core.workspace import WorkspaceApi
from tracim_backend.models.auth import User
from tracim_backend.models.data import UserRoleInWorkspace
from tracim_backend.models.revision_protection import new_revision
from tracim_backend.models.setup_models import get_tm_session
from tracim_backend.tests import FunctionalTest
from tracim_backend.tests import MailHogFunctionalTest
from tracim_backend.tests import set_html_document_slug_to_legacy


class TestWorkspaceEndpoint(FunctionalTest):
    """
    Tests for /api/v2/workspaces/{workspace_id} endpoint
    """

    fixtures = [BaseFixture, ContentFixtures]

    def test_api__get_workspace__ok_200__nominal_case(self) -> None:
        """
        Check obtain workspace reachable for user.
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.READER, False)
        workspace_api = WorkspaceApi(session=dbsession, current_user=admin, config=self.app_config)
        workspace = workspace_api.get_one(workspace.workspace_id)
        app_api = ApplicationApi(app_list)
        default_sidebar_entry = app_api.get_default_workspace_menu_entry(
            workspace=workspace
        )  # nope8
        transaction.commit()

        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        res = self.testapp.get("/api/v2/workspaces/{}".format(workspace.workspace_id), status=200)
        workspace_dict = res.json_body
        assert workspace_dict["workspace_id"] == workspace.workspace_id
        assert workspace_dict["label"] == workspace.label
        assert workspace_dict["description"] == workspace.description
        assert workspace_dict["is_deleted"] is False

        assert len(workspace_dict["sidebar_entries"]) == len(default_sidebar_entry)
        for counter, sidebar_entry in enumerate(default_sidebar_entry):
            workspace_dict["sidebar_entries"][counter]["slug"] = sidebar_entry.slug
            workspace_dict["sidebar_entries"][counter]["label"] = sidebar_entry.label
            workspace_dict["sidebar_entries"][counter]["route"] = sidebar_entry.route
            workspace_dict["sidebar_entries"][counter]["hexcolor"] = sidebar_entry.hexcolor
            workspace_dict["sidebar_entries"][counter]["fa_icon"] = sidebar_entry.fa_icon

    def test_api__get_workspace__ok_200__admin_and_not_in_workspace(self) -> None:
        """
        Check obtain workspace reachable for user.
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=None, session=dbsession, config=self.app_config)
        rapi.delete_one(admin.user_id, workspace.workspace_id)
        workspace_api = WorkspaceApi(session=dbsession, current_user=admin, config=self.app_config)
        workspace = workspace_api.get_one(workspace.workspace_id)
        app_api = ApplicationApi(app_list)
        default_sidebar_entry = app_api.get_default_workspace_menu_entry(
            workspace=workspace
        )  # nope8
        transaction.commit()

        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/{}".format(workspace.workspace_id), status=200)
        workspace_dict = res.json_body
        assert workspace_dict["workspace_id"] == workspace.workspace_id
        assert workspace_dict["label"] == workspace.label
        assert workspace_dict["description"] == workspace.description
        assert workspace_dict["is_deleted"] is False

        assert len(workspace_dict["sidebar_entries"]) == len(default_sidebar_entry)
        for counter, sidebar_entry in enumerate(default_sidebar_entry):
            workspace_dict["sidebar_entries"][counter]["slug"] = sidebar_entry.slug
            workspace_dict["sidebar_entries"][counter]["label"] = sidebar_entry.label
            workspace_dict["sidebar_entries"][counter]["route"] = sidebar_entry.route
            workspace_dict["sidebar_entries"][counter]["hexcolor"] = sidebar_entry.hexcolor
            workspace_dict["sidebar_entries"][counter]["fa_icon"] = sidebar_entry.fa_icon

    def test_api__update_workspace__ok_200__nominal_case(self) -> None:
        """
        Test update workspace
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()

        workspace_api = WorkspaceApi(session=dbsession, current_user=admin, config=self.app_config)
        workspace = workspace_api.get_one(1)
        app_api = ApplicationApi(app_list)
        default_sidebar_entry = app_api.get_default_workspace_menu_entry(
            workspace=workspace
        )  # nope8

        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {
            "label": "superworkspace",
            "description": "mysuperdescription",
            "agenda_enabled": False,
        }
        # Before
        res = self.testapp.get("/api/v2/workspaces/1", status=200)
        assert res.json_body
        workspace = res.json_body
        assert workspace["workspace_id"] == 1
        assert workspace["slug"] == "business"
        assert workspace["label"] == "Business"
        assert workspace["description"] == "All importants documents"
        assert len(workspace["sidebar_entries"]) == len(default_sidebar_entry)
        assert workspace["is_deleted"] is False
        assert workspace["agenda_enabled"] is True

        # modify workspace
        res = self.testapp.put_json("/api/v2/workspaces/1", status=200, params=params)
        assert res.json_body
        workspace = res.json_body
        assert workspace["workspace_id"] == 1
        assert workspace["slug"] == "superworkspace"
        assert workspace["label"] == "superworkspace"
        assert workspace["description"] == "mysuperdescription"
        assert len(workspace["sidebar_entries"]) == len(default_sidebar_entry)
        assert workspace["is_deleted"] is False
        assert workspace["agenda_enabled"] is False

        # after
        res = self.testapp.get("/api/v2/workspaces/1", status=200)
        assert res.json_body
        workspace = res.json_body
        assert workspace["workspace_id"] == 1
        assert workspace["slug"] == "superworkspace"
        assert workspace["label"] == "superworkspace"
        assert workspace["description"] == "mysuperdescription"
        assert len(workspace["sidebar_entries"]) == len(default_sidebar_entry)
        assert workspace["is_deleted"] is False
        assert workspace["agenda_enabled"] is False

    def test_api__update_workspace__err_400__workspace_label_already_used(self) -> None:
        """
        Test update workspace with empty label
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {
            "label": "Documentation",
            "description": "mysuperdescription",
            "agenda_enabled": False,
        }
        res = self.testapp.post_json("/api/v2/workspaces", status=200, params=params)
        workspace1_id = res.json_body["workspace_id"]

        params = {
            "label": "Documentation2",
            "description": "mysuperdescription",
            "agenda_enabled": False,
        }
        res = self.testapp.post_json("/api/v2/workspaces", status=200, params=params)
        workspace2_id = res.json_body["workspace_id"]

        assert workspace1_id != workspace2_id

        params = {"label": "Documentation", "description": "mysuperdescription"}
        # INFO - G.M - 2019-05-21 - we can update to same value
        self.testapp.put_json(
            "/api/v2/workspaces/{}".format(workspace1_id), status=200, params=params
        )
        # INFO - G.M - 2019-05-21 - updating one workspace to another workspace name is not allowed
        res = self.testapp.put_json(
            "/api/v2/workspaces/{}".format(workspace2_id), status=400, params=params
        )
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.WORKSPACE_LABEL_ALREADY_USED

    def test_api__update_workspace__err_400__empty_label(self) -> None:
        """
        Test update workspace with empty label
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"label": "", "description": "mysuperdescription"}
        res = self.testapp.put_json("/api/v2/workspaces/1", status=400, params=params)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.GENERIC_SCHEMA_VALIDATION_ERROR

    def test_api__create_workspace__ok_200__nominal_case(self) -> None:
        """
        Test create workspace
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {
            "label": "superworkspace",
            "description": "mysuperdescription",
            "agenda_enabled": False,
        }
        res = self.testapp.post_json("/api/v2/workspaces", status=200, params=params)
        assert res.json_body
        workspace = res.json_body
        assert workspace["label"] == "superworkspace"
        assert workspace["agenda_enabled"] is False
        assert workspace["description"] == "mysuperdescription"
        workspace_id = res.json_body["workspace_id"]
        res = self.testapp.get("/api/v2/workspaces/{}".format(workspace_id), status=200)
        workspace_2 = res.json_body
        assert workspace == workspace_2

    def test_api__create_workspace_err_400__label_already_used(self) -> None:
        """
        Test create workspace : label already used
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"label": "superworkspace", "description": "mysuperdescription"}
        self.testapp.post_json("/api/v2/workspaces", status=200, params=params)
        res = self.testapp.post_json("/api/v2/workspaces", status=400, params=params)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.WORKSPACE_LABEL_ALREADY_USED

    def test_api__create_workspace__err_400__empty_label(self) -> None:
        """
        Test create workspace with empty label
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"label": "", "description": "mysuperdescription"}
        res = self.testapp.post_json("/api/v2/workspaces", status=400, params=params)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.GENERIC_SCHEMA_VALIDATION_ERROR

    def test_api__delete_workspace__ok_200__admin(self) -> None:
        """
        Test delete workspace as admin
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        transaction.commit()
        workspace_id = int(workspace.workspace_id)
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        # delete
        self.testapp.put("/api/v2/workspaces/{}/trashed".format(workspace_id), status=204)
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        res = self.testapp.get("/api/v2/workspaces/{}".format(workspace_id), status=400)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.WORKSPACE_NOT_FOUND
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/{}".format(workspace_id), status=200)
        workspace = res.json_body
        assert workspace["is_deleted"] is True

    def test_api__delete_workspace__ok_200__manager_workspace_manager(self) -> None:
        """
        Test delete workspace as global manager and workspace manager
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        transaction.commit()
        workspace_id = int(workspace.workspace_id)
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        # delete
        self.testapp.put("/api/v2/workspaces/{}/trashed".format(workspace_id), status=204)
        res = self.testapp.get("/api/v2/workspaces/{}".format(workspace_id), status=200)
        workspace = res.json_body
        assert workspace["is_deleted"] is True

    def test_api__delete_workspace__err_403__user_workspace_manager(self) -> None:
        """
        Test delete workspace as simple user and workspace manager
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        transaction.commit()
        workspace_id = int(workspace.workspace_id)
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        # delete
        res = self.testapp.put("/api/v2/workspaces/{}/trashed".format(workspace_id), status=403)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.INSUFFICIENT_USER_PROFILE
        res = self.testapp.get("/api/v2/workspaces/{}".format(workspace_id), status=200)
        workspace = res.json_body
        assert workspace["is_deleted"] is False

    def test_api__delete_workspace__err_403__manager_reader(self) -> None:
        """
        Test delete workspace as manager and reader of the workspace
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        user = uapi.create_user(
            "test@test.test", password="test@test.test", do_save=True, do_notify=False
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.READER, False)
        transaction.commit()
        workspace_id = int(workspace.workspace_id)
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        # delete
        res = self.testapp.put("/api/v2/workspaces/{}/trashed".format(workspace_id), status=403)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.INSUFFICIENT_USER_ROLE_IN_WORKSPACE
        res = self.testapp.get("/api/v2/workspaces/{}".format(workspace_id), status=200)
        workspace = res.json_body
        assert workspace["is_deleted"] is False

    def test_api__delete_workspace__err_400__manager(self) -> None:
        """
        Test delete workspace as global manager without having any role in the
        workspace
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        uapi.create_user("test@test.test", password="test@test.test", do_save=True, do_notify=False)
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        transaction.commit()
        workspace_id = int(workspace.workspace_id)
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        # delete
        res = self.testapp.put("/api/v2/workspaces/{}/trashed".format(workspace_id), status=400)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.WORKSPACE_NOT_FOUND

    def test_api__undelete_workspace__ok_200__admin(self) -> None:
        """
        Test undelete workspace as admin
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        workspace_api.delete(workspace, flush=True)
        transaction.commit()
        workspace_id = int(workspace.workspace_id)
        # undelete
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        self.testapp.put("/api/v2/workspaces/{}/trashed/restore".format(workspace_id), status=204)
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        res = self.testapp.get("/api/v2/workspaces/{}".format(workspace_id), status=400)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.WORKSPACE_NOT_FOUND

        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/{}".format(workspace_id), status=200)
        workspace = res.json_body
        assert workspace["is_deleted"] is False

    def test_api__undelete_workspace__ok_200__manager_workspace_manager(self) -> None:
        """
        Test undelete workspace as global manager and workspace manager
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        workspace_api.delete(workspace, flush=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        transaction.commit()
        workspace_id = int(workspace.workspace_id)
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        # delete
        self.testapp.put("/api/v2/workspaces/{}/trashed/restore".format(workspace_id), status=204)
        res = self.testapp.get("/api/v2/workspaces/{}".format(workspace_id), status=200)
        workspace = res.json_body
        assert workspace["is_deleted"] is False

    def test_api__undelete_workspace__err_403__user_workspace_manager(self) -> None:
        """
        Test undelete workspace as simple user and workspace manager
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        workspace_api.delete(workspace, flush=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        transaction.commit()
        workspace_id = int(workspace.workspace_id)
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        # delete
        res = self.testapp.put(
            "/api/v2/workspaces/{}/trashed/restore".format(workspace_id), status=403
        )
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.INSUFFICIENT_USER_PROFILE
        res = self.testapp.get("/api/v2/workspaces/{}".format(workspace_id), status=200)
        workspace = res.json_body
        assert workspace["is_deleted"] is True

    def test_api__undelete_workspace__err_403__manager_reader(self) -> None:
        """
        Test undelete workspace as manager and reader of the workspace
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        user = uapi.create_user(
            "test@test.test", password="test@test.test", do_save=True, do_notify=False
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        workspace_api.delete(workspace, flush=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.READER, False)
        transaction.commit()
        workspace_id = int(workspace.workspace_id)
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        # delete
        res = self.testapp.put(
            "/api/v2/workspaces/{}/trashed/restore".format(workspace_id), status=403
        )
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.INSUFFICIENT_USER_ROLE_IN_WORKSPACE
        res = self.testapp.get("/api/v2/workspaces/{}".format(workspace_id), status=200)
        workspace = res.json_body
        assert workspace["is_deleted"] is True

    def test_api__undelete_workspace__err_400__manager(self) -> None:
        """
        Test delete workspace as global manager without having any role in the
        workspace
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        uapi.create_user("test@test.test", password="test@test.test", do_save=True, do_notify=False)
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        workspace_api.delete(workspace, flush=True)
        transaction.commit()
        workspace_id = int(workspace.workspace_id)
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        # delete
        res = self.testapp.put(
            "/api/v2/workspaces/{}/trashed/restore".format(workspace_id), status=400
        )
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.WORKSPACE_NOT_FOUND

    def test_api__get_workspace__err_400__unallowed_user(self) -> None:
        """
        Check obtain workspace unreachable for user
        """
        self.testapp.authorization = ("Basic", ("lawrence-not-real-email@fsf.local", "foobarbaz"))
        res = self.testapp.get("/api/v2/workspaces/1", status=400)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.WORKSPACE_NOT_FOUND
        assert "message" in res.json.keys()
        assert "details" in res.json.keys()

    def test_api__get_workspace__err_401__unregistered_user(self) -> None:
        """
        Check obtain workspace without registered user.
        """
        self.testapp.authorization = ("Basic", ("john@doe.doe", "lapin"))
        res = self.testapp.get("/api/v2/workspaces/1", status=401)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] is None
        assert "message" in res.json.keys()
        assert "details" in res.json.keys()

    def test_api__get_workspace__err_400__workspace_does_not_exist(self) -> None:
        """
        Check obtain workspace who does not exist with an existing user.
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/5", status=400)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.WORKSPACE_NOT_FOUND
        assert "message" in res.json.keys()
        assert "details" in res.json.keys()


class TestWorkspacesEndpoints(FunctionalTest):
    """
    Tests for /api/v2/workspaces
    """

    fixtures = [BaseFixture]

    def test_api__get_workspaces__ok_200__nominal_case(self):
        """
        Check obtain all workspaces reachables for user with user auth.
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()

        workspace_api = WorkspaceApi(session=dbsession, current_user=admin, config=self.app_config)
        workspace_api.create_workspace("test", save_now=True)
        workspace_api.create_workspace("test2", save_now=True)
        workspace_api.create_workspace("test3", save_now=True)
        transaction.commit()
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces", status=200)
        res = res.json_body
        assert len(res) == 3
        workspace = res[0]
        assert workspace["label"] == "test"
        assert workspace["slug"] == "test"
        workspace = res[1]
        assert workspace["label"] == "test2"
        assert workspace["slug"] == "test2"
        workspace = res[2]
        assert workspace["label"] == "test3"
        assert workspace["slug"] == "test3"

    def test_api__get_workspaces__err_403__unallowed_user(self):
        """
        Check obtain all workspaces reachables for one user
        with another non-admin user auth.
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("users")]
        uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        transaction.commit()
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        res = self.testapp.get("/api/v2/workspaces", status=403)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.INSUFFICIENT_USER_PROFILE
        assert "message" in res.json.keys()
        assert "details" in res.json.keys()

    def test_api__get_workspaces__err_401__unregistered_user(self):
        """
        Check obtain all workspaces reachables for one user
        without correct user auth (user unregistered).
        """
        self.testapp.authorization = ("Basic", ("john@doe.doe", "lapin"))
        res = self.testapp.get("/api/v2/workspaces", status=401)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] is None
        assert "message" in res.json.keys()
        assert "details" in res.json.keys()


class TestWorkspaceMembersEndpoint(FunctionalTest):
    """
    Tests for /api/v2/workspaces/{workspace_id}/members endpoint
    """

    fixtures = [BaseFixture, ContentFixtures]

    def test_api__get_workspace_members__ok_200__nominal_case(self):
        """
        Check obtain workspace members list with a reachable workspace for user
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/1/members", status=200).json_body
        assert len(res) == 1
        user_role = res[0]
        assert user_role["role"] == "workspace-manager"
        assert user_role["user_id"] == 1
        assert user_role["workspace_id"] == 1
        assert user_role["workspace"]["workspace_id"] == 1
        assert user_role["workspace"]["label"] == "Business"
        assert user_role["workspace"]["slug"] == "business"
        assert user_role["user"]["public_name"] == "Global manager"
        assert user_role["user"]["user_id"] == 1
        assert user_role["is_active"] is True
        assert user_role["do_notify"] is True
        # TODO - G.M - 24-05-2018 - [Avatar] Replace
        # by correct value when avatar feature will be enabled
        assert user_role["user"]["avatar_url"] is None

    def test_api__get_workspace_members__ok_200__as_admin(self):
        """
        Check obtain workspace members list of a workspace where admin doesn't
        have any right
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(current_user=admin, session=dbsession, config=self.app_config)
        workspace = workspace_api.create_workspace("test_2", save_now=True)
        rapi = RoleApi(current_user=None, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.READER, False)
        rapi.delete_one(admin.user_id, workspace.workspace_id)
        transaction.commit()
        user_id = user.user_id
        workspace_id = workspace.workspace_id
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get(
            "/api/v2/workspaces/{}/members".format(workspace_id, user_id), status=200
        ).json_body
        assert len(res) == 1
        user_role = res[0]
        assert user_role["role"] == "reader"
        assert user_role["user_id"] == user_id
        assert user_role["workspace_id"] == workspace_id
        assert user_role["is_active"] is True
        assert user_role["do_notify"] is False

    def test_api__get_workspace_members__err_400__unallowed_user(self):
        """
        Check obtain workspace members list with an unreachable workspace for
        user
        """
        self.testapp.authorization = ("Basic", ("lawrence-not-real-email@fsf.local", "foobarbaz"))
        res = self.testapp.get("/api/v2/workspaces/3/members", status=400)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.WORKSPACE_NOT_FOUND
        assert "message" in res.json.keys()
        assert "details" in res.json.keys()

    def test_api__get_workspace_members__err_401__unregistered_user(self):
        """
        Check obtain workspace members list with an unregistered user
        """
        self.testapp.authorization = ("Basic", ("john@doe.doe", "lapin"))
        res = self.testapp.get("/api/v2/workspaces/1/members", status=401)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] is None
        assert "message" in res.json.keys()
        assert "details" in res.json.keys()

    def test_api__get_workspace_member__ok_200__self(self):
        """
        Check obtain workspace members list with a reachable workspace for user
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/1/members/1", status=200).json_body
        user_role = res
        assert user_role["role"] == "workspace-manager"
        assert user_role["user_id"] == 1
        assert user_role["workspace_id"] == 1
        assert user_role["workspace"]["workspace_id"] == 1
        assert user_role["workspace"]["label"] == "Business"
        assert user_role["workspace"]["slug"] == "business"
        assert user_role["user"]["public_name"] == "Global manager"
        assert user_role["user"]["user_id"] == 1
        assert user_role["is_active"] is True
        assert user_role["do_notify"] is True
        # TODO - G.M - 24-05-2018 - [Avatar] Replace
        # by correct value when avatar feature will be enabled
        assert user_role["user"]["avatar_url"] is None

    def test_api__get_workspace_member__ok_200__as_admin(self):
        """
        Check obtain workspace members list with a reachable workspace for user
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(current_user=admin, session=dbsession, config=self.app_config)
        workspace = workspace_api.create_workspace("test_2", save_now=True)
        rapi = RoleApi(current_user=None, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.READER, False)
        rapi.delete_one(admin.user_id, workspace.workspace_id)
        transaction.commit()
        user_id = user.user_id
        workspace_id = workspace.workspace_id
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get(
            "/api/v2/workspaces/{}/members/{}".format(workspace_id, user_id), status=200
        ).json_body
        user_role = res
        assert user_role["role"] == "reader"
        assert user_role["user_id"] == user_id
        assert user_role["workspace_id"] == workspace_id
        assert user_role["is_active"] is True
        assert user_role["do_notify"] is False

    def test_api__get_workspace_member__ok_200__other_user(self):
        """
        Check obtain workspace members list with a reachable workspace for user
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(current_user=admin, session=dbsession, config=self.app_config)
        workspace = workspace_api.create_workspace("test_2", save_now=True)
        rapi = RoleApi(current_user=None, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.READER, False)
        transaction.commit()
        user_id = user.user_id
        workspace_id = workspace.workspace_id
        admin_id = admin.user_id
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get(
            "/api/v2/workspaces/{}/members/{}".format(workspace_id, user_id), status=200
        ).json_body
        user_role = res
        assert user_role["role"] == "reader"
        assert user_role["user_id"] == user_id
        assert user_role["workspace_id"] == workspace_id
        assert user_role["is_active"] is True
        assert user_role["do_notify"] is False

        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        res = self.testapp.get(
            "/api/v2/workspaces/{}/members/{}".format(workspace_id, admin_id), status=200
        ).json_body
        user_role = res
        assert user_role["role"] == "workspace-manager"
        assert user_role["user_id"] == admin_id
        assert user_role["workspace_id"] == workspace_id
        assert user_role["is_active"] is True
        assert user_role["do_notify"] is True

    def test_api__get_workspace_member__err_400__unallowed_user(self):
        """
        Check obtain workspace members info with an unreachable workspace for
        user
        """
        self.testapp.authorization = ("Basic", ("lawrence-not-real-email@fsf.local", "foobarbaz"))
        res = self.testapp.get("/api/v2/workspaces/3/members/1", status=400)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.WORKSPACE_NOT_FOUND
        assert "message" in res.json.keys()
        assert "details" in res.json.keys()

    def test_api__get_workspace_member__err_401__unregistered_user(self):
        """
        Check obtain workspace member info with an unregistered user
        """
        self.testapp.authorization = ("Basic", ("john@doe.doe", "lapin"))
        res = self.testapp.get("/api/v2/workspaces/1/members/1", status=401)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] is None
        assert "message" in res.json.keys()
        assert "details" in res.json.keys()

    def test_api__get_workspace_members__err_400__workspace_does_not_exist(self):
        """
        Check obtain workspace members list with an existing user but
        an unexisting workspace
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/5/members", status=400)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.WORKSPACE_NOT_FOUND
        assert "message" in res.json.keys()
        assert "details" in res.json.keys()

    def test_api__create_workspace_member_role__ok_200__user_id(self):
        """
        Create workspace member role
        :return:
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        # create workspace role
        params = {
            "user_id": 2,
            "user_email": None,
            "user_public_name": None,
            "role": "content-manager",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/members", status=200, params=params)
        user_role_found = res.json_body
        assert user_role_found["role"] == "content-manager"
        assert user_role_found["user_id"] == 2
        assert user_role_found["workspace_id"] == 1
        assert user_role_found["newly_created"] is False
        assert user_role_found["email_sent"] is False
        assert user_role_found["do_notify"] is False

        res = self.testapp.get("/api/v2/workspaces/1/members", status=200).json_body
        assert len(res) == 2
        user_role = res[0]
        assert user_role["role"] == "workspace-manager"
        assert user_role["user_id"] == 1
        assert user_role["workspace_id"] == 1
        user_role = res[1]
        assert user_role_found["role"] == user_role["role"]
        assert user_role_found["user_id"] == user_role["user_id"]
        assert user_role_found["workspace_id"] == user_role["workspace_id"]

    def test_api__create_workspace_members_role_ok_200__user_email_as_admin(self):
        """
        Check obtain workspace members list of a workspace where admin doesn't
        have any right
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        workspace_api = WorkspaceApi(current_user=admin, session=dbsession, config=self.app_config)
        workspace = workspace_api.create_workspace("test_2", save_now=True)
        rapi = RoleApi(current_user=None, session=dbsession, config=self.app_config)
        rapi.delete_one(admin.user_id, workspace.workspace_id)
        transaction.commit()
        workspace_id = workspace.workspace_id
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        # create workspace role
        params = {
            "user_id": None,
            "user_email": "lawrence-not-real-email@fsf.local",
            "user_public_name": None,
            "role": "content-manager",
        }
        res = self.testapp.post_json(
            "/api/v2/workspaces/{}/members".format(workspace_id), status=200, params=params
        )
        user_role_found = res.json_body
        assert user_role_found["role"] == "content-manager"
        assert user_role_found["user_id"]
        assert user_role_found["workspace_id"] == workspace_id
        assert user_role_found["newly_created"] is False
        assert user_role_found["email_sent"] is False
        assert user_role_found["do_notify"] is False

        res = self.testapp.get(
            "/api/v2/workspaces/{}/members".format(workspace_id), status=200
        ).json_body
        assert len(res) == 1
        user_role = res[0]
        assert user_role_found["role"] == user_role["role"]
        assert user_role_found["user_id"] == user_role["user_id"]
        assert user_role_found["workspace_id"] == user_role["workspace_id"]

    def test_api__create_workspace_members_role_ok_200__user_email_as_workspace_manager(self):
        """
        Check obtain workspace members list of a workspace where admin doesn't
        have any right
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(current_user=admin, session=dbsession, config=self.app_config)
        workspace = workspace_api.create_workspace("test_2", save_now=True)
        rapi = RoleApi(current_user=None, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        rapi.delete_one(admin.user_id, workspace.workspace_id)
        transaction.commit()
        user_id = user.user_id
        workspace_id = workspace.workspace_id
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        # create workspace role
        params = {
            "user_id": None,
            "user_email": "lawrence-not-real-email@fsf.local",
            "user_public_name": None,
            "role": "content-manager",
        }
        res = self.testapp.post_json(
            "/api/v2/workspaces/{}/members".format(workspace_id), status=200, params=params
        )
        user_role_found = res.json_body
        assert user_role_found["role"] == "content-manager"
        assert user_role_found["user_id"]
        assert user_role_found["workspace_id"] == workspace_id
        assert user_role_found["newly_created"] is False
        assert user_role_found["email_sent"] is False
        assert user_role_found["do_notify"] is False

        res = self.testapp.get(
            "/api/v2/workspaces/{}/members".format(workspace_id), status=200
        ).json_body
        assert len(res) == 2
        user_role = res[0]
        assert user_role_found["role"] == user_role["role"]
        assert user_role_found["user_id"] == user_role["user_id"]
        assert user_role_found["workspace_id"] == user_role["workspace_id"]
        user_role = res[1]
        assert user_role["role"] == "workspace-manager"
        assert user_role["user_id"] == user_id
        assert user_role["workspace_id"] == workspace_id

    def test_api__create_workspace_member_role__ok_200__user_email(self):
        """
        Create workspace member role
        :return:
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        # create workspace role
        params = {
            "user_id": None,
            "user_email": "lawrence-not-real-email@fsf.local",
            "user_public_name": None,
            "role": "content-manager",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/members", status=200, params=params)
        user_role_found = res.json_body
        assert user_role_found["role"] == "content-manager"
        assert user_role_found["user_id"] == 2
        assert user_role_found["workspace_id"] == 1
        assert user_role_found["newly_created"] is False
        assert user_role_found["email_sent"] is False
        assert user_role_found["do_notify"] is False

        res = self.testapp.get("/api/v2/workspaces/1/members", status=200).json_body
        assert len(res) == 2
        user_role = res[0]
        assert user_role["role"] == "workspace-manager"
        assert user_role["user_id"] == 1
        assert user_role["workspace_id"] == 1
        user_role = res[1]
        assert user_role_found["role"] == user_role["role"]
        assert user_role_found["user_id"] == user_role["user_id"]
        assert user_role_found["workspace_id"] == user_role["workspace_id"]

    def test_api__create_workspace_member_role__err_400__user_email__user_deactivated(self):
        """
        Create workspace member role
        :return:
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        lawrence = uapi.get_one_by_email("lawrence-not-real-email@fsf.local")
        lawrence.is_active = False
        uapi.save(lawrence)
        transaction.commit()
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))

        # create workspace role
        params = {
            "user_id": None,
            "user_email": "lawrence-not-real-email@fsf.local",
            "user_public_name": None,
            "role": "content-manager",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/members", status=400, params=params)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.USER_NOT_ACTIVE

    def test_api__create_workspace_member_role__err_400__user_email__user_deleted(self):
        """
        Create workspace member role
        :return:
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        lawrence = uapi.get_one_by_email("lawrence-not-real-email@fsf.local")
        lawrence.is_deleted = True
        uapi.save(lawrence)
        transaction.commit()
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))

        # create workspace role
        params = {
            "user_id": None,
            "user_email": "lawrence-not-real-email@fsf.local",
            "user_public_name": None,
            "role": "content-manager",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/members", status=400, params=params)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.USER_DELETED

    def test_api__create_workspace_member_role__ok_200__user_public_name(self):
        """
        Create workspace member role
        :return:
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        # create workspace role
        params = {
            "user_id": None,
            "user_email": None,
            "user_public_name": "Lawrence L.",
            "role": "content-manager",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/members", status=200, params=params)
        user_role_found = res.json_body
        assert user_role_found["role"] == "content-manager"
        assert user_role_found["user_id"] == 2
        assert user_role_found["workspace_id"] == 1
        assert user_role_found["newly_created"] is False
        assert user_role_found["email_sent"] is False
        assert user_role_found["do_notify"] is False

        res = self.testapp.get("/api/v2/workspaces/1/members", status=200).json_body
        assert len(res) == 2
        user_role = res[0]
        assert user_role["role"] == "workspace-manager"
        assert user_role["user_id"] == 1
        assert user_role["workspace_id"] == 1
        user_role = res[1]
        assert user_role_found["role"] == user_role["role"]
        assert user_role_found["user_id"] == user_role["user_id"]
        assert user_role_found["workspace_id"] == user_role["workspace_id"]

    def test_api__create_workspace_member_role__ok_400__user_public_name_user_already_in_workspace(
        self
    ):
        """
        Create workspace member role
        :return:
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        # create workspace role
        params = {
            "user_id": None,
            "user_email": None,
            "user_public_name": "Lawrence L.",
            "role": "content-manager",
        }
        self.testapp.post_json("/api/v2/workspaces/1/members", status=200, params=params)
        res = self.testapp.post_json("/api/v2/workspaces/1/members", status=400, params=params)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.USER_ROLE_ALREADY_EXIST

    def test_api__create_workspace_member_role__err_400__nothing_and_no_notification(self):
        """
        Create workspace member role
        :return:
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        # create workspace role
        params = {
            "user_id": None,
            "user_email": None,
            "user_public_name": None,
            "role": "content-manager",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/members", status=400, params=params)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.USER_NOT_FOUND

    def test_api__create_workspace_member_role__err_400__wrong_user_id_and_not_notification(self):
        """
        Create workspace member role
        :return:
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        # create workspace role
        params = {
            "user_id": 47,
            "user_email": None,
            "user_public_name": None,
            "role": "content-manager",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/members", status=400, params=params)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.USER_NOT_FOUND

    def test_api__create_workspace_member_role__err_400__notification_disabled_user_not_found(self):
        """
        Create workspace member role
        :return:
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        # create workspace role
        params = {
            "user_id": None,
            "user_email": "nothing@nothing.nothing",
            "user_public_name": None,
            "role": "content-manager",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/members", status=400, params=params)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.USER_NOT_FOUND

    def test_api__update_workspace_member_role__ok_200__nominal_case(self):
        """
        Update worskpace member role
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        user2 = uapi.create_user(
            "test2@test2.test2",
            password="test2@test2.test2",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=None, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        rapi.create_one(user2, workspace, UserRoleInWorkspace.READER, False)
        rapi.delete_one(admin.user_id, workspace.workspace_id)
        transaction.commit()
        # before
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        self.testapp.get(
            "/api/v2/workspaces/{workspace_id}/members/{user_id}".format(
                workspace_id=workspace.workspace_id, user_id=user2.user_id
            ),
            status=200,
        )
        # update workspace role
        params = {"role": "content-manager"}
        res = self.testapp.put_json(
            "/api/v2/workspaces/{workspace_id}/members/{user_id}".format(
                workspace_id=workspace.workspace_id, user_id=user2.user_id
            ),
            status=200,
            params=params,
        )
        user_role = res.json_body
        assert user_role["role"] == "content-manager"
        assert user_role["user_id"] == user2.user_id
        assert user_role["workspace_id"] == workspace.workspace_id
        # after
        res = self.testapp.get(
            "/api/v2/workspaces/{workspace_id}/members/{user_id}".format(
                workspace_id=workspace.workspace_id, user_id=user2.user_id
            ),
            status=200,
        ).json_body
        user_role = res
        assert user_role["role"] == "content-manager"
        assert user_role["do_notify"] is False
        assert user_role["user_id"] == user2.user_id
        assert user_role["workspace_id"] == workspace.workspace_id

    def test_api__update_workspace_member_role__err_400__role_not_exist(self):
        """
        Update worskpace member role
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        user2 = uapi.create_user(
            "test2@test2.test2",
            password="test2@test2.test2",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=None, session=dbsession, config=self.app_config)
        rapi.delete_one(admin.user_id, workspace.workspace_id)
        transaction.commit()
        # update workspace role
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"role": "content-manager"}
        res = self.testapp.put_json(
            "/api/v2/workspaces/{workspace_id}/members/{user_id}".format(
                workspace_id=workspace.workspace_id, user_id=user2.user_id
            ),
            status=400,
            params=params,
        )
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.USER_ROLE_NOT_FOUND

    def test_api__update_workspace_member_role__ok_200__as_admin(self):
        """
        Update worskpace member role
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        user2 = uapi.create_user(
            "test2@test2.test2",
            password="test2@test2.test2",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=None, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        rapi.create_one(user2, workspace, UserRoleInWorkspace.READER, False)
        rapi.delete_one(admin.user_id, workspace.workspace_id)
        transaction.commit()
        # before
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        self.testapp.get(
            "/api/v2/workspaces/{workspace_id}/members/{user_id}".format(
                workspace_id=workspace.workspace_id, user_id=user2.user_id
            ),
            status=200,
        )
        # update workspace role
        params = {"role": "content-manager"}
        res = self.testapp.put_json(
            "/api/v2/workspaces/{workspace_id}/members/{user_id}".format(
                workspace_id=workspace.workspace_id, user_id=user2.user_id
            ),
            status=200,
            params=params,
        )
        user_role = res.json_body
        assert user_role["role"] == "content-manager"
        assert user_role["user_id"] == user2.user_id
        assert user_role["workspace_id"] == workspace.workspace_id
        # after
        res = self.testapp.get(
            "/api/v2/workspaces/{workspace_id}/members/{user_id}".format(
                workspace_id=workspace.workspace_id, user_id=user2.user_id
            ),
            status=200,
        ).json_body
        user_role = res
        assert user_role["role"] == "content-manager"
        assert user_role["do_notify"] is False
        assert user_role["user_id"] == user2.user_id
        assert user_role["workspace_id"] == workspace.workspace_id

    def test_api__delete_workspace_member_role__ok_200__as_admin(self):
        """
        Delete worskpace member role
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        transaction.commit()

        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        self.testapp.delete(
            "/api/v2/workspaces/{workspace_id}/members/{user_id}".format(
                workspace_id=workspace.workspace_id, user_id=user.user_id
            ),
            status=204,
        )
        # after
        roles = self.testapp.get(
            "/api/v2/workspaces/{}/members".format(workspace.workspace_id), status=200
        ).json_body
        for role in roles:
            assert role["user_id"] != user.user_id

    def test_api__delete_workspace_member_role__ok_200__nominal_case(self):
        """
        Delete worskpace member role
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        user2 = uapi.create_user(
            "test2@test2.test2",
            password="test2@test2.test2",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        rapi.create_one(user2, workspace, UserRoleInWorkspace.READER, False)
        transaction.commit()

        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        self.testapp.delete(
            "/api/v2/workspaces/{workspace_id}/members/{user_id}".format(
                workspace_id=workspace.workspace_id, user_id=user2.user_id
            ),
            status=204,
        )
        # after
        roles = self.testapp.get(
            "/api/v2/workspaces/{}/members".format(workspace.workspace_id), status=200
        ).json_body
        for role in roles:
            assert role["user_id"] != user2.user_id

    def test_api__delete_workspace_member_role__err_400__role_not_exist(self):
        """
        Delete worskpace member role
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        user2 = uapi.create_user(
            "test2@test2.test2",
            password="test2@test2.test2",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        transaction.commit()

        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.delete(
            "/api/v2/workspaces/{workspace_id}/members/{user_id}".format(
                workspace_id=workspace.workspace_id, user_id=user2.user_id
            ),
            status=400,
        )
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.USER_ROLE_NOT_FOUND

    def test_api__delete_workspace_member_role__err_400__workspace_manager_itself(self):
        """
        Delete worskpace member role.
        Unallow to delete himself as workspace_manager
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        user2 = uapi.create_user(
            "test2@test2.test2",
            password="test2@test2.test2",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        rapi.create_one(user2, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        transaction.commit()

        self.testapp.authorization = ("Basic", ("test2@test2.test2", "test2@test2.test2"))
        res = self.testapp.delete(
            "/api/v2/workspaces/{workspace_id}/members/{user_id}".format(
                workspace_id=workspace.workspace_id, user_id=user2.user_id
            ),
            status=400,
        )
        assert res.json_body["code"] == ErrorCode.USER_CANT_REMOVE_IS_OWN_ROLE_IN_WORKSPACE
        # after
        roles = self.testapp.get(
            "/api/v2/workspaces/{}/members".format(workspace.workspace_id), status=200
        ).json_body
        assert user2.user_id in [role["user_id"] for role in roles]

    def test_api__delete_workspace_member_role__err_400__simple_user(self):
        """
        Delete worskpace member role
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("users")]
        user2 = uapi.create_user(
            "test2@test2.test2",
            password="test2@test2.test2",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        groups = [gapi.get_one_with_name("trusted-users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        rapi.create_one(user2, workspace, UserRoleInWorkspace.READER, False)
        transaction.commit()

        self.testapp.authorization = ("Basic", ("test2@test2.test2", "test2@test2.test2"))
        res = self.testapp.delete(
            "/api/v2/workspaces/{workspace_id}/members/{user_id}".format(
                workspace_id=workspace.workspace_id, user_id=user.user_id
            ),
            status=403,
        )
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.INSUFFICIENT_USER_ROLE_IN_WORKSPACE
        # after
        roles = self.testapp.get(
            "/api/v2/workspaces/{workspace_id}/members".format(workspace_id=workspace.workspace_id),
            status=200,
        ).json_body
        assert len([role for role in roles if role["user_id"] == user.user_id]) == 1


class TestUserInvitationWithMailActivatedSync(MailHogFunctionalTest):

    fixtures = [BaseFixture, ContentFixtures]
    config_section = "functional_test_with_mail_test_sync"

    def test_api__create_workspace_member_role__ok_200__new_user(self):
        """
        Create workspace member role
        :return:
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        transaction.commit()
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        # create workspace role
        params = {
            "user_id": None,
            "user_public_name": None,
            "user_email": "bob@bob.bob",
            "role": "content-manager",
        }
        res = self.testapp.post_json(
            "/api/v2/workspaces/{}/members".format(workspace.workspace_id),
            status=200,
            params=params,
        )
        user_role_found = res.json_body
        assert user_role_found["role"] == "content-manager"
        assert user_role_found["user_id"]
        user_id = user_role_found["user_id"]
        assert user_role_found["workspace_id"] == workspace.workspace_id
        assert user_role_found["newly_created"] is True
        assert user_role_found["email_sent"] is True
        assert user_role_found["do_notify"] is False

        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/users/{}".format(user_id), status=200)
        res = res.json_body
        assert res["profile"] == "users"

        # check mail received
        response = self.get_mailhog_mails()
        assert len(response) == 1
        headers = response[0]["Content"]["Headers"]
        assert headers["From"][0] == "Tracim Notifications <test_user_from+0@localhost>"
        assert headers["To"][0] == "bob <bob@bob.bob>"
        assert headers["Subject"][0] == "[TRACIM] Created account"

    def test_api__create_workspace_member_role__err_400__user_not_found_as_simple_user(self):
        """
        Create workspace member role
        :return:
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        transaction.commit()

        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        # create workspace role
        params = {
            "user_id": None,
            "user_public_name": None,
            "user_email": "bob@bob.bob",
            "role": "content-manager",
        }
        res = self.testapp.post_json(
            "/api/v2/workspaces/{}/members".format(workspace.workspace_id),
            status=400,
            params=params,
        )
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.USER_NOT_FOUND


class TestUserInvitationWithMailActivatedSyncWithNotification(MailHogFunctionalTest):

    fixtures = [BaseFixture, ContentFixtures]
    config_section = "functional_test_with_mail_test_sync_with_auto_notif"

    def test_api__create_workspace_member_role__ok_200__new_user_notif(self):
        """
        Create workspace member role
        :return:
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("trusted-users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.WORKSPACE_MANAGER, False)
        transaction.commit()

        self.cleanup_mailhog()
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        # create workspace role
        params = {
            "user_id": None,
            "user_public_name": None,
            "user_email": "bob@bob.bob",
            "role": "content-manager",
        }
        res = self.testapp.post_json(
            "/api/v2/workspaces/{}/members".format(workspace.workspace_id),
            status=200,
            params=params,
        )
        user_role_found = res.json_body
        assert user_role_found["role"] == "content-manager"
        assert user_role_found["user_id"]
        user_id = user_role_found["user_id"]
        assert user_role_found["workspace_id"] == workspace.workspace_id
        assert user_role_found["newly_created"] is True
        assert user_role_found["email_sent"] is True
        assert user_role_found["do_notify"] is True

        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/users/{}".format(user_id), status=200)
        res = res.json_body
        assert res["profile"] == "users"

        # check mail received
        response = self.get_mailhog_mails()
        assert len(response) == 1
        headers = response[0]["Content"]["Headers"]
        assert headers["From"][0] == "Tracim Notifications <test_user_from+0@localhost>"
        assert headers["To"][0] == "bob <bob@bob.bob>"
        assert headers["Subject"][0] == "[TRACIM] Created account"
        # check for notification to new user, user should not be notified
        # until it connected to tracim.
        self.cleanup_mailhog()
        api = ContentApi(session=dbsession, current_user=admin, config=self.app_config)
        api.create(
            content_type_slug="html-document",
            workspace=workspace,
            label="test_document",
            do_save=True,
        )
        transaction.commit()
        response = self.get_mailhog_mails()
        assert len(response) == 0
        # check for notification to new connected user, user should not be notified
        # until it connected to tracim.
        bob = uapi.get_one_by_email(email="bob@bob.bob")
        uapi.update(user=bob, password="bob@bob.bob", do_save=True)
        transaction.commit()
        self.testapp.authorization = ("Basic", ("bob@bob.bob", "bob@bob.bob"))
        self.testapp.get("/api/v2/auth/whoami", status=200)
        self.cleanup_mailhog()
        api = ContentApi(session=dbsession, current_user=admin, config=self.app_config)
        api.create(
            content_type_slug="html-document",
            workspace=workspace,
            label="test_document2",
            do_save=True,
        )
        transaction.commit()
        response = self.get_mailhog_mails()
        assert len(response) == 1
        headers = response[0]["Content"]["Headers"]
        assert headers["From"][0] == "Global manager via Tracim <test_user_from+1@localhost>"
        assert headers["To"][0] == "bob <bob@bob.bob>"
        assert headers["Subject"][0] == "[TRACIM] [test] test_document2 (Open)"


class TestUserInvitationWithMailActivatedSyncLDAPAuthOnly(FunctionalTest):

    fixtures = [BaseFixture, ContentFixtures]
    config_section = "functional_test_with_mail_test_sync_ldap_auth_only"

    def test_api__create_workspace_member_role__ok_200__new_user_but_internal_auth_disabled(self):
        """
        Create workspace member role
        :return:
        """
        self.testapp.authorization = ("Basic", ("hubert@planetexpress.com", "professor"))
        res = self.testapp.get("/api/v2/auth/whoami", status=200)
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        uapi = UserApi(current_user=None, session=self.session, config=self.app_config)
        user = uapi.get_one_by_email("hubert@planetexpress.com")
        gapi = GroupApi(session=self.session, config=self.app_config, current_user=user)
        uapi.update(
            user, auth_type=user.auth_type, groups=[gapi.get_one_with_name("administrators")]
        )
        uapi.save(user)
        transaction.commit()
        workspace_api = WorkspaceApi(
            current_user=user, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        transaction.commit()

        # create workspace role
        params = {
            "user_id": None,
            "user_public_name": None,
            "user_email": "bob@bob.bob",
            "role": "content-manager",
        }
        res = self.testapp.post_json(
            "/api/v2/workspaces/{}/members".format(workspace.workspace_id),
            status=200,
            params=params,
        )
        user_id = res.json_body["user_id"]
        assert res.json_body["role"] == "content-manager"
        assert res.json_body["user"]["public_name"] == "bob"
        res = self.testapp.get("/api/v2/users/{}".format(user_id), status=200, params=params)
        assert res.json_body["auth_type"] == "unknown"
        assert res.json_body["email"] == "bob@bob.bob"


class TestUserInvitationWithMailActivatedSyncEmailNotifDisabledButInvitationEmailEnabled(
    FunctionalTest
):

    fixtures = [BaseFixture, ContentFixtures]
    config_section = "functional_test_with_no_email_notif_but_invitation_email_notif"

    def test_api__create_workspace_member_role__err_400__email_notif_disabe_but_invitation_notif_enabled(
        self
    ):
        """
        Create workspace member role
        :return:
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        transaction.commit()

        # create workspace role
        params = {
            "user_id": None,
            "user_public_name": None,
            "user_email": "bob@bob.bob",
            "role": "content-manager",
        }
        res = self.testapp.post_json(
            "/api/v2/workspaces/{}/members".format(workspace.workspace_id),
            status=400,
            params=params,
        )
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.USER_NOT_FOUND


class TestUserInvitationWithMailActivatedSyncEmailNotifDisabledAndInvitationEmailDisabled(
    FunctionalTest
):

    fixtures = [BaseFixture, ContentFixtures]
    config_section = "functional_test_with_no_email_notif_and_no_invitation_email_notif"

    def test_api__create_workspace_member_role__ok_200__email_notif_disabe_but_invitation_notif_enabled(
        self
    ):
        """
        Create workspace member role
        :return:
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        transaction.commit()

        # create workspace role
        params = {
            "user_id": None,
            "user_public_name": None,
            "user_email": "bob@bob.bob",
            "role": "content-manager",
        }
        res = self.testapp.post_json(
            "/api/v2/workspaces/{}/members".format(workspace.workspace_id),
            status=200,
            params=params,
        )
        user_id = res.json_body["user_id"]
        assert res.json_body["role"] == "content-manager"
        assert res.json_body["user"]["public_name"] == "bob"
        res = self.testapp.get("/api/v2/users/{}".format(user_id), status=200, params=params)
        assert res.json_body["auth_type"] == "unknown"
        assert res.json_body["email"] == "bob@bob.bob"


class TestUserInvitationWithMailActivatedSyncEmailEnabledAndInvitationEmailDisabled(FunctionalTest):

    fixtures = [BaseFixture, ContentFixtures]
    config_section = "functional_test_with_email_notif_and_no_invitation_email_notif"

    def test_api__create_workspace_member_role__ok_200__email_notif_disabe_but_invitation_notif_enabled(
        self
    ):
        """
        Create workspace member role
        :return:
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        transaction.commit()

        # create workspace role
        params = {
            "user_id": None,
            "user_public_name": None,
            "user_email": "bob@bob.bob",
            "role": "content-manager",
        }
        res = self.testapp.post_json(
            "/api/v2/workspaces/{}/members".format(workspace.workspace_id),
            status=200,
            params=params,
        )
        user_id = res.json_body["user_id"]
        assert res.json_body["role"] == "content-manager"
        assert res.json_body["user"]["public_name"] == "bob"
        res = self.testapp.get("/api/v2/users/{}".format(user_id), status=200, params=params)
        assert res.json_body["auth_type"] == "unknown"
        assert res.json_body["email"] == "bob@bob.bob"


class TestUserInvitationWithMailActivatedASync(FunctionalTest):

    fixtures = [BaseFixture, ContentFixtures]
    config_section = "functional_test_with_mail_test_async"

    def test_api__create_workspace_member_role__ok_200__new_user(self):
        """
        Create workspace member role
        :return:
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        # create workspace role
        params = {
            "user_id": None,
            "user_public_name": None,
            "user_email": "bob@bob.bob",
            "role": "content-manager",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/members", status=200, params=params)
        user_role_found = res.json_body
        assert user_role_found["newly_created"] is True
        assert user_role_found["email_sent"] is False


class TestWorkspaceContents(FunctionalTest):
    """
    Tests for /api/v2/workspaces/{workspace_id}/contents endpoint
    """

    fixtures = [BaseFixture, ContentFixtures]

    def test_api__get_workspace_content__ok_200__get_default(self):
        """
        Check obtain workspace contents with defaults filters
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/1/contents", status=200).json_body
        # TODO - G.M - 30-05-2018 - Check this test
        assert len(res) == 3
        content = res[0]
        assert content["content_id"] == 11
        assert content["content_type"] == "html-document"
        assert content["is_archived"] is False
        assert content["is_deleted"] is False
        assert content["label"] == "Current Menu"
        assert content["parent_id"] == 2
        assert content["show_in_ui"] is True
        assert content["slug"] == "current-menu"
        assert content["status"] == "open"
        assert content["modified"]
        assert content["created"]
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 1
        content = res[1]
        assert content["content_id"] == 2
        assert content["content_type"] == "folder"
        assert content["is_archived"] is False
        assert content["is_deleted"] is False
        assert content["label"] == "Menus"
        assert content["parent_id"] is None
        assert content["show_in_ui"] is True
        assert content["slug"] == "menus"
        assert content["status"] == "open"
        assert len(content["sub_content_types"]) > 1
        assert "comment" in content["sub_content_types"]
        assert "folder" in content["sub_content_types"]
        assert content["workspace_id"] == 1
        assert content["modified"]
        assert content["created"]
        content = res[2]
        assert content["content_id"] == 1
        assert content["content_type"] == "folder"
        assert content["is_archived"] is False
        assert content["is_deleted"] is False
        assert content["label"] == "Tools"
        assert content["parent_id"] is None
        assert content["show_in_ui"] is True
        assert content["slug"] == "tools"
        assert content["status"] == "open"
        assert len(content["sub_content_types"]) > 1
        assert "comment" in content["sub_content_types"]
        assert "folder" in content["sub_content_types"]
        assert content["workspace_id"] == 1
        assert content["modified"]
        assert content["created"]

    def test_api__get_workspace_content__ok_200__get_default_html_documents(self):
        """
        Check obtain workspace contents with defaults filters + content_filter
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"content_type": "html-document"}
        res = self.testapp.get("/api/v2/workspaces/1/contents", status=200, params=params).json_body
        assert len(res) == 1
        content = res[0]
        assert content
        assert content["content_id"] == 11
        assert content["content_type"] == "html-document"
        assert content["is_archived"] is False
        assert content["is_deleted"] is False
        assert content["label"] == "Current Menu"
        assert content["parent_id"] == 2
        assert content["show_in_ui"] is True
        assert content["slug"] == "current-menu"
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 1
        assert content["modified"]
        assert content["created"]

    def test_api__get_workspace_content__ok_200__get_all_root_content__legacy_html_slug(self):
        """
        Check obtain workspace all root contents
        """
        set_html_document_slug_to_legacy(self.session_factory)
        params = {"parent_id": 0, "show_archived": 1, "show_deleted": 1, "show_active": 1}
        self.testapp.authorization = ("Basic", ("bob@fsf.local", "foobarbaz"))
        res = self.testapp.get("/api/v2/workspaces/3/contents", status=200, params=params).json_body
        # TODO - G.M - 30-05-2018 - Check this test
        assert len(res) == 4
        content = res[0]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 17
        assert content["is_archived"] is False
        assert content["is_deleted"] is True
        assert content["label"].startswith("Bad Fruit Salad")
        assert content["parent_id"] is None
        assert content["show_in_ui"] is True
        assert content["slug"].startswith("bad-fruit-salad")
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 3
        assert content["modified"]
        assert content["created"]
        content = res[1]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 16
        assert content["is_archived"] is True
        assert content["is_deleted"] is False
        assert content["label"].startswith("Fruit Salad")
        assert content["parent_id"] is None
        assert content["show_in_ui"] is True
        assert content["slug"].startswith("fruit-salad")
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 3
        assert content["modified"]
        assert content["created"]
        content = res[3]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 15
        assert content["is_archived"] is False
        assert content["is_deleted"] is False
        assert content["label"] == "New Fruit Salad"
        assert content["parent_id"] is None
        assert content["show_in_ui"] is True
        assert content["slug"] == "new-fruit-salad"
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 3
        assert content["modified"]
        assert content["created"]

    def test_api__get_workspace_content__ok_200__get_all_root_content(self):
        """
        Check obtain workspace all root contents
        """
        params = {"parent_id": 0, "show_archived": 1, "show_deleted": 1, "show_active": 1}
        self.testapp.authorization = ("Basic", ("bob@fsf.local", "foobarbaz"))
        res = self.testapp.get("/api/v2/workspaces/3/contents", status=200, params=params).json_body
        # TODO - G.M - 30-05-2018 - Check this test
        assert len(res) == 4
        content = res[0]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 17
        assert content["is_archived"] is False
        assert content["is_deleted"] is True
        assert content["label"].startswith("Bad Fruit Salad")
        assert content["parent_id"] is None
        assert content["show_in_ui"] is True
        assert content["slug"].startswith("bad-fruit-salad")
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 3
        assert content["modified"]
        assert content["created"]
        content = res[1]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 16
        assert content["is_archived"] is True
        assert content["is_deleted"] is False
        assert content["label"].startswith("Fruit Salad")
        assert content["parent_id"] is None
        assert content["show_in_ui"] is True
        assert content["slug"].startswith("fruit-salad")
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 3
        assert content["modified"]
        assert content["created"]
        content = res[3]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 15
        assert content["is_archived"] is False
        assert content["is_deleted"] is False
        assert content["label"] == "New Fruit Salad"
        assert content["parent_id"] is None
        assert content["show_in_ui"] is True
        assert content["slug"] == "new-fruit-salad"
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 3
        assert content["modified"]
        assert content["created"]

    def test_api__get_workspace_content__ok_200__get_all_root_and_folder_content(self):
        """
        Check obtain workspace all root contents and all subcontent content
        """
        params = {"parent_ids": "0,3", "show_archived": 1, "show_deleted": 1, "show_active": 1}
        self.testapp.authorization = ("Basic", ("bob@fsf.local", "foobarbaz"))
        res = self.testapp.get("/api/v2/workspaces/2/contents", status=200, params=params).json_body
        # TODO - G.M - 30-05-2018 - Check this test
        assert len(res) == 7
        assert [
            content
            for content in res
            if content["label"] == "Desserts"
            and content["content_type"] == "folder"
            and content["parent_id"] is None
            and content["content_id"] == 3
        ]
        assert [
            content
            for content in res
            if content["label"] == "Fruits Desserts"
            and content["content_type"] == "folder"
            and content["parent_id"] == 3
        ]

    def test_api__get_workspace_content__ok_200__get_multiple_folder_content(self):
        """
        Check obtain workspace all root contents and all subcontent content
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"parent_id": 1, "label": "GenericCreatedContent", "content_type": "html-document"}
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        content_id = res.json_body["content_id"]
        params = {"parent_ids": "1,2", "show_archived": 1, "show_deleted": 1, "show_active": 1}
        res = self.testapp.get("/api/v2/workspaces/1/contents", status=200, params=params).json_body
        # TODO - G.M - 30-05-2018 - Check this test
        assert len(res) == 2
        assert [
            content
            for content in res
            if content["label"] == "Current Menu"
            and content["content_type"] == "html-document"
            and content["parent_id"] == 2
            and content["content_id"] == 11
        ]
        assert [
            content
            for content in res
            if content["label"] == "GenericCreatedContent"
            and content["content_type"] == "html-document"
            and content["parent_id"] == 1
            and content["content_id"] == content_id
        ]

    def test_api__get_workspace_content__ok_200__get_folder_content_with_path_of_content(self):
        """
        Check obtain workspace all root contents and all subcontent content
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"parent_id": 1, "label": "subfolder", "content_type": "folder"}
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        subfolder_content_id = res.json_body["content_id"]
        params = {
            "parent_id": subfolder_content_id,
            "label": "subsubfolder",
            "content_type": "folder",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        subsubfolder_content_id = res.json_body["content_id"]
        params = {
            "parent_id": subsubfolder_content_id,
            "label": "InfolderContent",
            "content_type": "html-document",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        infolder_content_id = res.json_body["content_id"]
        params = {"parent_id": 1, "label": "GenericCreatedContent", "content_type": "html-document"}
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        generic_content_content_id = res.json_body["content_id"]
        params = {
            "parent_ids": "2",
            "complete_path_to_id": infolder_content_id,
            "show_archived": 1,
            "show_deleted": 1,
            "show_active": 1,
        }
        res = self.testapp.get("/api/v2/workspaces/1/contents", status=200, params=params).json_body
        # TODO - G.M - 30-05-2018 - Check this test
        assert len(res) == 7
        assert [
            content
            for content in res
            if content["label"] == "Current Menu"
            and content["content_type"] == "html-document"
            and content["parent_id"] == 2
            and content["content_id"] == 11
        ]
        assert [
            content
            for content in res
            if content["label"] == "GenericCreatedContent"
            and content["content_type"] == "html-document"
            and content["parent_id"] == 1
            and content["content_id"] == generic_content_content_id
        ]
        assert [
            content
            for content in res
            if content["label"] == "InfolderContent"
            and content["content_type"] == "html-document"
            and content["parent_id"] == subsubfolder_content_id
            and content["content_id"] == infolder_content_id
        ]
        assert [
            content
            for content in res
            if content["label"] == "subsubfolder"
            and content["content_type"] == "folder"
            and content["parent_id"] == subfolder_content_id
            and content["content_id"] == subsubfolder_content_id
        ]
        assert [
            content
            for content in res
            if content["label"] == "subfolder"
            and content["content_type"] == "folder"
            and content["parent_id"] == 1
            and content["content_id"] == subfolder_content_id
        ]

    def test_api__get_workspace_content__ok_200__get_path_of_content(self):
        """
        Check obtain workspace all root contents and all subcontent content
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"parent_id": 1, "label": "subfolder", "content_type": "folder"}
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        subfolder_content_id = res.json_body["content_id"]
        params = {
            "parent_id": subfolder_content_id,
            "label": "subsubfolder",
            "content_type": "folder",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        subsubfolder_content_id = res.json_body["content_id"]
        params = {
            "parent_id": subsubfolder_content_id,
            "label": "InfolderContent",
            "content_type": "html-document",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        infolder_content_id = res.json_body["content_id"]
        params = {"parent_id": 1, "label": "GenericCreatedContent", "content_type": "html-document"}
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        generic_content_content_id = res.json_body["content_id"]
        params = {
            "complete_path_to_id": infolder_content_id,
            "show_archived": 1,
            "show_deleted": 1,
            "show_active": 1,
        }
        res = self.testapp.get("/api/v2/workspaces/1/contents", status=200, params=params).json_body
        # TODO - G.M - 30-05-2018 - Check this test
        assert len(res) == 6
        assert [
            content
            for content in res
            if content["label"] == "GenericCreatedContent"
            and content["content_type"] == "html-document"
            and content["parent_id"] == 1
            and content["content_id"] == generic_content_content_id
        ]
        assert [
            content
            for content in res
            if content["label"] == "InfolderContent"
            and content["content_type"] == "html-document"
            and content["parent_id"] == subsubfolder_content_id
            and content["content_id"] == infolder_content_id
        ]
        assert [
            content
            for content in res
            if content["label"] == "subsubfolder"
            and content["content_type"] == "folder"
            and content["parent_id"] == subfolder_content_id
            and content["content_id"] == subsubfolder_content_id
        ]
        assert [
            content
            for content in res
            if content["label"] == "subfolder"
            and content["content_type"] == "folder"
            and content["parent_id"] == 1
            and content["content_id"] == subfolder_content_id
        ]

    def test_api__get_workspace_content__ok_200__get_path_of_content_deleted_content(self):
        """
        Check obtain workspace all root contents and all subcontent content
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"parent_id": 1, "label": "subfolder", "content_type": "folder"}
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        subfolder_content_id = res.json_body["content_id"]
        params = {
            "parent_id": subfolder_content_id,
            "label": "subsubfolder",
            "content_type": "folder",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        subsubfolder_content_id = res.json_body["content_id"]
        params = {
            "parent_id": subsubfolder_content_id,
            "label": "InfolderContent",
            "content_type": "html-document",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        infolder_content_id = res.json_body["content_id"]
        # delete
        res = self.testapp.put_json(
            "/api/v2/workspaces/1/contents/{}/trashed".format(infolder_content_id), status=204
        )
        params = {"parent_id": 1, "label": "GenericCreatedContent", "content_type": "html-document"}
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        generic_content_content_id = res.json_body["content_id"]
        params = {
            "complete_path_to_id": infolder_content_id,
            "show_archived": 1,
            "show_deleted": 1,
            "show_active": 1,
        }
        res = self.testapp.get("/api/v2/workspaces/1/contents", status=200, params=params).json_body
        # TODO - G.M - 30-05-2018 - Check this test
        assert len(res) == 6
        assert [
            content
            for content in res
            if content["label"] == "GenericCreatedContent"
            and content["content_type"] == "html-document"
            and content["parent_id"] == 1
            and content["content_id"] == generic_content_content_id
        ]
        assert [
            content
            for content in res
            if content["label"].startswith("InfolderContent")
            and content["content_type"] == "html-document"
            and content["parent_id"] == subsubfolder_content_id
            and content["content_id"] == infolder_content_id
            and content["is_deleted"] is True
        ]
        assert [
            content
            for content in res
            if content["label"] == "subsubfolder"
            and content["content_type"] == "folder"
            and content["parent_id"] == subfolder_content_id
            and content["content_id"] == subsubfolder_content_id
        ]
        assert [
            content
            for content in res
            if content["label"] == "subfolder"
            and content["content_type"] == "folder"
            and content["parent_id"] == 1
            and content["content_id"] == subfolder_content_id
        ]

        params = {
            "complete_path_to_id": infolder_content_id,
            "show_archived": 1,
            "show_deleted": 0,
            "show_active": 1,
        }
        res = self.testapp.get("/api/v2/workspaces/1/contents", status=200, params=params).json_body
        assert len(res) == 5
        assert [
            content
            for content in res
            if content["label"] == "GenericCreatedContent"
            and content["content_type"] == "html-document"
            and content["parent_id"] == 1
            and content["content_id"] == generic_content_content_id
        ]
        assert not [
            content
            for content in res
            if content["label"].startswith("InfolderContent")
            and content["content_type"] == "html-document"
            and content["parent_id"] == subsubfolder_content_id
            and content["content_id"] == infolder_content_id
            and content["is_deleted"] is True
        ]
        assert [
            content
            for content in res
            if content["label"] == "subsubfolder"
            and content["content_type"] == "folder"
            and content["parent_id"] == subfolder_content_id
            and content["content_id"] == subsubfolder_content_id
        ]
        assert [
            content
            for content in res
            if content["label"] == "subfolder"
            and content["content_type"] == "folder"
            and content["parent_id"] == 1
            and content["content_id"] == subfolder_content_id
        ]

    def test_api__get_workspace_content__ok_200__get_path_of_content_archived_content(self):
        """
        Check obtain workspace all root contents and all subcontent content
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"parent_id": 1, "label": "subfolder", "content_type": "folder"}
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        subfolder_content_id = res.json_body["content_id"]
        params = {
            "parent_id": subfolder_content_id,
            "label": "subsubfolder",
            "content_type": "folder",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        subsubfolder_content_id = res.json_body["content_id"]
        params = {
            "parent_id": subsubfolder_content_id,
            "label": "InfolderContent",
            "content_type": "html-document",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        infolder_content_id = res.json_body["content_id"]
        params = {"parent_id": 1, "label": "GenericCreatedContent", "content_type": "html-document"}
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        generic_content_content_id = res.json_body["content_id"]
        # archive
        res = self.testapp.put_json(
            "/api/v2/workspaces/1/contents/{}/archived".format(infolder_content_id), status=204
        )
        params = {
            "complete_path_to_id": infolder_content_id,
            "show_archived": 1,
            "show_deleted": 1,
            "show_active": 1,
        }
        res = self.testapp.get("/api/v2/workspaces/1/contents", status=200, params=params).json_body
        # TODO - G.M - 30-05-2018 - Check this test
        assert len(res) == 6
        assert [
            content
            for content in res
            if content["label"] == "GenericCreatedContent"
            and content["content_type"] == "html-document"
            and content["parent_id"] == 1
            and content["content_id"] == generic_content_content_id
        ]
        assert [
            content
            for content in res
            if content["label"].startswith("InfolderContent")
            and content["content_type"] == "html-document"
            and content["parent_id"] == subsubfolder_content_id
            and content["content_id"] == infolder_content_id
            and content["is_archived"] is True
        ]
        assert [
            content
            for content in res
            if content["label"] == "subsubfolder"
            and content["content_type"] == "folder"
            and content["parent_id"] == subfolder_content_id
            and content["content_id"] == subsubfolder_content_id
        ]
        assert [
            content
            for content in res
            if content["label"] == "subfolder"
            and content["content_type"] == "folder"
            and content["parent_id"] == 1
            and content["content_id"] == subfolder_content_id
        ]

        params = {
            "complete_path_to_id": infolder_content_id,
            "show_archived": 0,
            "show_deleted": 1,
            "show_active": 1,
        }
        res = self.testapp.get("/api/v2/workspaces/1/contents", status=200, params=params).json_body
        assert len(res) == 5
        assert [
            content
            for content in res
            if content["label"] == "GenericCreatedContent"
            and content["content_type"] == "html-document"
            and content["parent_id"] == 1
            and content["content_id"] == generic_content_content_id
        ]
        assert not [
            content
            for content in res
            if content["label"].startswith("InfolderContent")
            and content["content_type"] == "html-document"
            and content["parent_id"] == subsubfolder_content_id
            and content["content_id"] == infolder_content_id
            and content["is_archived"] is True
        ]
        assert [
            content
            for content in res
            if content["label"] == "subsubfolder"
            and content["content_type"] == "folder"
            and content["parent_id"] == subfolder_content_id
            and content["content_id"] == subsubfolder_content_id
        ]
        assert [
            content
            for content in res
            if content["label"] == "subfolder"
            and content["content_type"] == "folder"
            and content["parent_id"] == 1
            and content["content_id"] == subfolder_content_id
        ]

    def test_api__get_workspace_content__ok_200__get_all_root_content_filter_by_label(self):
        """
        Check obtain workspace all root contents
        """
        params = {
            "parent_id": 0,
            "show_archived": 1,
            "show_deleted": 1,
            "show_active": 1,
            "label": "ew",
        }
        self.testapp.authorization = ("Basic", ("bob@fsf.local", "foobarbaz"))
        res = self.testapp.get("/api/v2/workspaces/3/contents", status=200, params=params).json_body
        # TODO - G.M - 30-05-2018 - Check this test
        assert len(res) == 1
        content = res[0]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 15
        assert content["is_archived"] is False
        assert content["is_deleted"] is False
        assert content["label"] == "New Fruit Salad"
        assert content["parent_id"] is None
        assert content["show_in_ui"] is True
        assert content["slug"] == "new-fruit-salad"
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 3
        assert content["modified"]
        assert content["created"]

    def test_api__get_workspace_content__ok_200__get_only_active_root_content(self):
        """
        Check obtain workspace root active contents
        """
        params = {"parent_id": 0, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        self.testapp.authorization = ("Basic", ("bob@fsf.local", "foobarbaz"))
        res = self.testapp.get("/api/v2/workspaces/3/contents", status=200, params=params).json_body
        # TODO - G.M - 30-05-2018 - Check this test
        assert len(res) == 2
        content = res[1]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 15
        assert content["is_archived"] is False
        assert content["is_deleted"] is False
        assert content["label"] == "New Fruit Salad"
        assert content["parent_id"] is None
        assert content["show_in_ui"] is True
        assert content["slug"] == "new-fruit-salad"
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 3
        assert content["modified"]
        assert content["created"]

    def test_api__get_workspace_content__ok_200__get_only_archived_root_content(self):
        """
        Check obtain workspace root archived contents
        """
        params = {"parent_id": 0, "show_archived": 1, "show_deleted": 0, "show_active": 0}
        self.testapp.authorization = ("Basic", ("bob@fsf.local", "foobarbaz"))
        res = self.testapp.get("/api/v2/workspaces/3/contents", status=200, params=params).json_body
        assert len(res) == 1
        content = res[0]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 16
        assert content["is_archived"] is True
        assert content["is_deleted"] is False
        assert content["label"].startswith("Fruit Salad")
        assert content["parent_id"] is None
        assert content["show_in_ui"] is True
        assert content["slug"].startswith("fruit-salad")
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 3
        assert content["modified"]
        assert content["created"]

    def test_api__get_workspace_content__ok_200__get_only_deleted_root_content(self):
        """
         Check obtain workspace root deleted contents
         """
        params = {"parent_id": 0, "show_archived": 0, "show_deleted": 1, "show_active": 0}
        self.testapp.authorization = ("Basic", ("bob@fsf.local", "foobarbaz"))
        res = self.testapp.get("/api/v2/workspaces/3/contents", status=200, params=params).json_body
        # TODO - G.M - 30-05-2018 - Check this test

        assert len(res) == 1
        content = res[0]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 17
        assert content["is_archived"] is False
        assert content["is_deleted"] is True
        assert content["label"].startswith("Bad Fruit Salad")
        assert content["parent_id"] is None
        assert content["show_in_ui"] is True
        assert content["slug"].startswith("bad-fruit-salad")
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 3
        assert content["modified"]
        assert content["created"]

    def test_api__get_workspace_content__ok_200__get_nothing_root_content(self):
        """
        Check obtain workspace root content who does not match any type
        (archived, deleted, active) result should be empty list.
        """
        params = {"parent_id": 0, "show_archived": 0, "show_deleted": 0, "show_active": 0}
        self.testapp.authorization = ("Basic", ("bob@fsf.local", "foobarbaz"))
        res = self.testapp.get("/api/v2/workspaces/3/contents", status=200, params=params).json_body
        # TODO - G.M - 30-05-2018 - Check this test
        assert res == []

    # Folder related
    def test_api__get_workspace_content__ok_200__get_all_filter_content_thread(self):
        # prepare data
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        workspace_api = WorkspaceApi(current_user=admin, session=dbsession, config=self.app_config)
        business_workspace = workspace_api.get_one(1)
        content_api = ContentApi(current_user=admin, session=dbsession, config=self.app_config)
        tool_folder = content_api.get_one(1, content_type=content_type_list.Any_SLUG)
        test_thread = content_api.create(
            content_type_slug=content_type_list.Thread.slug,
            workspace=business_workspace,
            parent=tool_folder,
            label="Test Thread",
            do_save=False,
            do_notify=False,
        )
        test_thread.description = "Thread description"
        dbsession.add(test_thread)
        test_file = content_api.create(
            content_type_slug=content_type_list.File.slug,
            workspace=business_workspace,
            parent=tool_folder,
            label="Test file",
            do_save=False,
            do_notify=False,
        )
        test_file.file_extension = ".txt"
        test_file.depot_file = FileIntent(b"Test file", "Test_file.txt", "text/plain")
        test_page_legacy = content_api.create(
            content_type_slug=content_type_list.Page.slug,
            workspace=business_workspace,
            label="test_page",
            do_save=False,
            do_notify=False,
        )
        test_page_legacy.type = "page"
        with new_revision(session=dbsession, tm=transaction.manager, content=test_page_legacy):
            content_api.update_content(test_page_legacy, "test_page", "<p>PAGE</p>")
        test_html_document = content_api.create(
            content_type_slug=content_type_list.Page.slug,
            workspace=business_workspace,
            label="test_html_page",
            do_save=False,
            do_notify=False,
        )
        with new_revision(session=dbsession, tm=transaction.manager, content=test_html_document):
            content_api.update_content(test_html_document, "test_page", "<p>HTML_DOCUMENT</p>")
        dbsession.flush()
        transaction.commit()
        # test-itself
        params = {
            "parent_id": 1,
            "show_archived": 1,
            "show_deleted": 1,
            "show_active": 1,
            "content_type": "thread",
        }
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/1/contents", status=200, params=params).json_body
        assert len(res) == 1
        content = res[0]
        assert content["content_type"] == "thread"
        assert content["content_id"]
        assert content["is_archived"] is False
        assert content["is_deleted"] is False
        assert content["label"] == "Test Thread"
        assert content["parent_id"] == 1
        assert content["show_in_ui"] is True
        assert content["slug"] == "test-thread"
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 1
        assert content["modified"]
        assert content["created"]

    def test_api__get_workspace_content__ok_200__get_all_filter_content_html_and_legacy_page(self):
        # prepare data
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        workspace_api = WorkspaceApi(current_user=admin, session=dbsession, config=self.app_config)
        business_workspace = workspace_api.get_one(1)
        content_api = ContentApi(current_user=admin, session=dbsession, config=self.app_config)
        tool_folder = content_api.get_one(1, content_type=content_type_list.Any_SLUG)
        test_thread = content_api.create(
            content_type_slug=content_type_list.Thread.slug,
            workspace=business_workspace,
            parent=tool_folder,
            label="Test Thread",
            do_save=False,
            do_notify=False,
        )
        test_thread.description = "Thread description"
        dbsession.add(test_thread)
        test_file = content_api.create(
            content_type_slug=content_type_list.File.slug,
            workspace=business_workspace,
            parent=tool_folder,
            label="Test file",
            do_save=False,
            do_notify=False,
        )
        test_file.file_extension = ".txt"
        test_file.depot_file = FileIntent(b"Test file", "Test_file.txt", "text/plain")
        test_page_legacy = content_api.create(
            content_type_slug=content_type_list.Page.slug,
            workspace=business_workspace,
            parent=tool_folder,
            label="test_page",
            do_save=False,
            do_notify=False,
        )
        test_page_legacy.type = "page"
        with new_revision(session=dbsession, tm=transaction.manager, content=test_page_legacy):
            content_api.update_content(test_page_legacy, "test_page", "<p>PAGE</p>")
        test_html_document = content_api.create(
            content_type_slug=content_type_list.Page.slug,
            workspace=business_workspace,
            parent=tool_folder,
            label="test_html_page",
            do_save=False,
            do_notify=False,
        )
        with new_revision(session=dbsession, tm=transaction.manager, content=test_html_document):
            content_api.update_content(test_html_document, "test_html_page", "<p>HTML_DOCUMENT</p>")
            dbsession.flush()
        transaction.commit()
        # test-itself
        params = {
            "parent_ids": 1,
            "show_archived": 1,
            "show_deleted": 1,
            "show_active": 1,
            "content_type": "html-document",
        }
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/1/contents", status=200, params=params).json_body
        assert len(res) == 2
        content = res[0]
        assert content["content_type"] == "html-document"
        assert content["content_id"]
        assert content["is_archived"] is False
        assert content["is_deleted"] is False
        assert content["label"] == "test_html_page"
        assert content["parent_id"] == 1
        assert content["show_in_ui"] is True
        assert content["slug"] == "test-html-page"
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 1
        assert res[0]["content_id"] != res[1]["content_id"]
        assert content["modified"]
        assert content["created"]
        content = res[1]
        assert content["content_type"] == "html-document"
        assert content["content_id"]
        assert content["is_archived"] is False
        assert content["is_deleted"] is False
        assert content["label"] == "test_page"
        assert content["parent_id"] == 1
        assert content["show_in_ui"] is True
        assert content["slug"] == "test-page"
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 1
        assert content["modified"]
        assert content["created"]

    def test_api__get_workspace_content__ok_200__get_all_folder_content(self):
        """
         Check obtain workspace folder all contents
         """
        params = {
            "parent_ids": 10,  # TODO - G.M - 30-05-2018 - Find a real id
            "show_archived": 1,
            "show_deleted": 1,
            "show_active": 1,
            #   'content_type': 'any'
        }
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/2/contents", status=200, params=params).json_body
        assert len(res) == 3
        content = res[0]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 14
        assert content["is_archived"] is False
        assert content["is_deleted"] is True
        assert content["label"].startswith("Bad Fruit Salad")
        assert content["parent_id"] == 10
        assert content["show_in_ui"] is True
        assert content["slug"].startswith("bad-fruit-salad")
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 2
        assert content["modified"]
        assert content["created"]
        content = res[1]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 13
        assert content["is_archived"] is True
        assert content["is_deleted"] is False
        assert content["label"].startswith("Fruit Salad")
        assert content["parent_id"] == 10
        assert content["show_in_ui"] is True
        assert content["slug"].startswith("fruit-salad")
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 2
        assert content["modified"]
        assert content["created"]
        content = res[2]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 12
        assert content["is_archived"] is False
        assert content["is_deleted"] is False
        assert content["label"] == "New Fruit Salad"
        assert content["parent_id"] == 10
        assert content["show_in_ui"] is True
        assert content["slug"] == "new-fruit-salad"
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 2
        assert content["modified"]
        assert content["created"]

    def test_api__get_workspace_content__ok_200__get_only_active_folder_content(self):
        """
         Check obtain workspace folder active contents
         """
        params = {"parent_ids": 10, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/2/contents", status=200, params=params).json_body
        assert len(res) == 1
        content = res[0]
        assert content["content_type"]
        assert content["content_id"] == 12
        assert content["is_archived"] is False
        assert content["is_deleted"] is False
        assert content["label"] == "New Fruit Salad"
        assert content["parent_id"] == 10
        assert content["show_in_ui"] is True
        assert content["slug"] == "new-fruit-salad"
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 2
        assert content["modified"]
        assert content["created"]

    def test_api__get_workspace_content__ok_200__get_only_archived_folder_content(self):
        """
         Check obtain workspace folder archived contents
         """
        params = {"parent_ids": 10, "show_archived": 1, "show_deleted": 0, "show_active": 0}
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/2/contents", status=200, params=params).json_body
        assert len(res) == 1
        content = res[0]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 13
        assert content["is_archived"] is True
        assert content["is_deleted"] is False
        assert content["label"].startswith("Fruit Salad")
        assert content["parent_id"] == 10
        assert content["show_in_ui"] is True
        assert content["slug"].startswith("fruit-salad")
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 2
        assert content["modified"]
        assert content["created"]

    def test_api__get_workspace_content__ok_200__get_only_deleted_folder_content(self):
        """
         Check obtain workspace folder deleted contents
         """
        params = {"parent_ids": 10, "show_archived": 0, "show_deleted": 1, "show_active": 0}
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/2/contents", status=200, params=params).json_body

        assert len(res) == 1
        content = res[0]
        assert content["content_type"] == "html-document"
        assert content["content_id"] == 14
        assert content["is_archived"] is False
        assert content["is_deleted"] is True
        assert content["label"].startswith("Bad Fruit Salad")
        assert content["parent_id"] == 10
        assert content["show_in_ui"] is True
        assert content["slug"].startswith("bad-fruit-salad")
        assert content["status"] == "open"
        assert set(content["sub_content_types"]) == {"comment"}
        assert content["workspace_id"] == 2
        assert content["modified"]
        assert content["created"]

    def test_api__get_workspace_content__ok_200__get_nothing_folder_content(self):
        """
        Check obtain workspace folder content who does not match any type
        (archived, deleted, active) result should be empty list.
        """
        params = {"parent_ids": 10, "show_archived": 0, "show_deleted": 0, "show_active": 0}
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/2/contents", status=200, params=params).json_body
        # TODO - G.M - 30-05-2018 - Check this test
        assert res == []

    # Error case

    def test_api__get_workspace_content__err_400__unallowed_user(self):
        """
        Check obtain workspace content list with an unreachable workspace for
        user
        """
        self.testapp.authorization = ("Basic", ("lawrence-not-real-email@fsf.local", "foobarbaz"))
        res = self.testapp.get("/api/v2/workspaces/3/contents", status=400)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.WORKSPACE_NOT_FOUND
        assert "message" in res.json.keys()
        assert "details" in res.json.keys()

    def test_api__get_workspace_content__err_401__unregistered_user(self):
        """
        Check obtain workspace content list with an unregistered user
        """
        self.testapp.authorization = ("Basic", ("john@doe.doe", "lapin"))
        res = self.testapp.get("/api/v2/workspaces/1/contents", status=401)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] is None
        assert "message" in res.json.keys()
        assert "details" in res.json.keys()

    def test_api__get_workspace_content__err_400__workspace_does_not_exist(self):
        """
        Check obtain workspace contents list with an existing user but
        an unexisting workspace
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        res = self.testapp.get("/api/v2/workspaces/5/contents", status=400)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.WORKSPACE_NOT_FOUND
        assert "message" in res.json.keys()
        assert "details" in res.json.keys()

    def test_api__post_content_create_generic_content__ok_200__nominal_case(self) -> None:
        """
        Create generic content as workspace root
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {
            "parent_id": None,
            "label": "GenericCreatedContent",
            "content_type": "html-document",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        assert res
        assert res.json_body
        assert res.json_body["status"] == "open"
        assert res.json_body["content_id"]
        assert res.json_body["content_type"] == "html-document"
        assert res.json_body["is_archived"] is False
        assert res.json_body["is_deleted"] is False
        assert res.json_body["workspace_id"] == 1
        assert res.json_body["slug"] == "genericcreatedcontent"
        assert res.json_body["parent_id"] is None
        assert res.json_body["show_in_ui"] is True
        assert res.json_body["sub_content_types"]
        assert res.json_body["modified"]
        assert res.json_body["created"]
        assert res.json_body["file_extension"] == ".document.html"
        assert res.json_body["filename"] == "GenericCreatedContent.document.html"
        params_active = {"parent_ids": 0, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        # INFO - G.M - 2018-06-165 - Verify if new content is correctly created
        active_contents = self.testapp.get(
            "/api/v2/workspaces/1/contents", params=params_active, status=200
        ).json_body
        content_ids = [content["content_id"] for content in active_contents]
        assert res.json_body["content_id"] in content_ids

    def test_api__post_content_create_generic_content__err_400__filename_already_used(self) -> None:
        """
        Create generic content but filename is already used here
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {
            "parent_id": None,
            "label": "GenericCreatedContent",
            "content_type": "html-document",
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        assert res
        assert res.json_body
        assert res.json_body["status"] == "open"
        assert res.json_body["content_id"]
        assert res.json_body["content_type"] == "html-document"
        assert res.json_body["is_archived"] is False
        assert res.json_body["is_deleted"] is False
        assert res.json_body["workspace_id"] == 1
        assert res.json_body["slug"] == "genericcreatedcontent"
        assert res.json_body["parent_id"] is None
        assert res.json_body["show_in_ui"] is True
        assert res.json_body["sub_content_types"]
        assert res.json_body["file_extension"] == ".document.html"
        assert res.json_body["filename"] == "GenericCreatedContent.document.html"
        assert res.json_body["modified"]
        assert res.json_body["created"]
        params_active = {"parent_ids": 0, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        # INFO - G.M - 2018-06-165 - Verify if new content is correctly created
        active_contents = self.testapp.get(
            "/api/v2/workspaces/1/contents", params=params_active, status=200
        ).json_body
        content_ids = [content["content_id"] for content in active_contents]
        assert res.json_body["content_id"] in content_ids

        # recreate same content
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=400)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.CONTENT_FILENAME_ALREADY_USED_IN_FOLDER

    def test_api__post_content_create_generic_content__ok_200__no_parent_id_param(self) -> None:
        """
        Create generic content without provided parent_id param
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"label": "GenericCreatedContent", "content_type": "html-document"}
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=200)
        assert res
        assert res.json_body
        assert res.json_body["status"] == "open"
        assert res.json_body["content_id"]
        assert res.json_body["content_type"] == "html-document"
        assert res.json_body["is_archived"] is False
        assert res.json_body["is_deleted"] is False
        assert res.json_body["workspace_id"] == 1
        assert res.json_body["slug"] == "genericcreatedcontent"
        assert res.json_body["parent_id"] is None
        assert res.json_body["show_in_ui"] is True
        assert res.json_body["sub_content_types"]
        assert res.json_body["file_extension"] == ".document.html"
        assert res.json_body["filename"] == "GenericCreatedContent.document.html"
        assert res.json_body["modified"]
        assert res.json_body["created"]
        params_active = {"parent_ids": 0, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        # INFO - G.M - 2018-06-165 - Verify if new content is correctly created
        active_contents = self.testapp.get(
            "/api/v2/workspaces/1/contents", params=params_active, status=200
        ).json_body
        content_ids = [content["content_id"] for content in active_contents]
        assert res.json_body["content_id"] in content_ids

    def test_api__post_content_create_generic_content__err_400__parent_id_0(self) -> None:
        """
        Create generic content but parent_id=0
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {
            "parent_id": 0,
            "label": "GenericCreatedContent",
            "content_type": content_type_list.Page.slug,
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=400)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        # INFO - G.M - 2018-09-10 - handled by marshmallow schema
        assert res.json_body["code"] == ErrorCode.GENERIC_SCHEMA_VALIDATION_ERROR

    def test_api__post_content_create_generic_content__err_400__parent_not_found(self) -> None:
        """
        Create generic content but parent id is not valable
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {
            "parent_id": 1000,
            "label": "GenericCreatedContent",
            "content_type": content_type_list.Page.slug,
        }
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=400)
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.PARENT_NOT_FOUND

    def test_api__post_content_create_generic_content__ok_200__in_folder(self) -> None:
        """
        Create generic content in folder
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {
            "label": "GenericCreatedContent",
            "content_type": "html-document",
            "parent_id": 10,
        }
        res = self.testapp.post_json("/api/v2/workspaces/2/contents", params=params, status=200)
        assert res
        assert res.json_body
        assert res.json_body["status"] == "open"
        assert res.json_body["content_id"]
        assert res.json_body["content_type"] == "html-document"
        assert res.json_body["is_archived"] is False
        assert res.json_body["is_deleted"] is False
        assert res.json_body["workspace_id"] == 2
        assert res.json_body["slug"] == "genericcreatedcontent"
        assert res.json_body["parent_id"] == 10
        assert res.json_body["show_in_ui"] is True
        assert res.json_body["sub_content_types"]
        assert res.json_body["file_extension"] == ".document.html"
        assert res.json_body["filename"] == "GenericCreatedContent.document.html"
        assert res.json_body["modified"]
        assert res.json_body["created"]
        params_active = {"parent_ids": 10, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        # INFO - G.M - 2018-06-165 - Verify if new content is correctly created
        active_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_active, status=200
        ).json_body
        content_ids = [content["content_id"] for content in active_contents]
        assert res.json_body["content_id"] in content_ids

    def test_api__post_content_create_generic_content__err_400__empty_label(self) -> None:
        """
        Create generic content but label provided is empty
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"label": "", "content_type": content_type_list.Page.slug}
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=400)
        # INFO - G.M - 2018-09-10 - handled by marshmallow schema
        assert res.json_body["code"] == ErrorCode.GENERIC_SCHEMA_VALIDATION_ERROR

    def test_api__post_content_create_generic_content__err_400__wrong_content_type(self) -> None:
        """
        Create generic content but content type is uncorrect
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"label": "GenericCreatedContent", "content_type": "unexistent-content-type"}
        res = self.testapp.post_json("/api/v2/workspaces/1/contents", params=params, status=400)
        assert res.json_body["code"] == ErrorCode.CONTENT_TYPE_NOT_EXIST

    def test_api__post_content_create_generic_content__err_400__unallowed_content_type(
        self
    ) -> None:
        """
        Create generic content but content_type is not allowed in this folder
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        workspace_api = WorkspaceApi(current_user=admin, session=dbsession, config=self.app_config)
        content_api = ContentApi(current_user=admin, session=dbsession, config=self.app_config)
        test_workspace = workspace_api.create_workspace(label="test", save_now=True)
        folder = content_api.create(
            label="test-folder",
            content_type_slug=content_type_list.Folder.slug,
            workspace=test_workspace,
            do_save=False,
            do_notify=False,
        )
        content_api.set_allowed_content(folder, [content_type_list.Folder.slug])
        content_api.save(folder)
        transaction.commit()
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        # unallowed_content_type
        params = {
            "label": "GenericCreatedContent",
            "content_type": content_type_list.Page.slug,
            "parent_id": folder.content_id,
        }
        res = self.testapp.post_json(
            "/api/v2/workspaces/{workspace_id}/contents".format(
                workspace_id=test_workspace.workspace_id
            ),
            params=params,
            status=400,
        )
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.UNALLOWED_SUBCONTENT
        # allowed_content_type
        params = {
            "label": "GenericCreatedContent",
            "content_type": "folder",
            "parent_ids": folder.content_id,
        }
        res = self.testapp.post_json(
            "/api/v2/workspaces/{workspace_id}/contents".format(
                workspace_id=test_workspace.workspace_id
            ),
            params=params,
            status=200,
        )

    def test_api__post_content_create_generic_content__err_403__try_creating_folder_as_simple_contributor(
        self
    ) -> None:
        """
        Create generic content but content_type is not allowed in this folder
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.CONTRIBUTOR, False)
        content_api = ContentApi(current_user=admin, session=dbsession, config=self.app_config)
        folder = content_api.create(
            label="test-folder",
            content_type_slug=content_type_list.Folder.slug,
            workspace=workspace,
            do_save=False,
            do_notify=False,
        )
        content_api.set_allowed_content(folder, [content_type_list.Folder.slug])
        content_api.save(folder)
        transaction.commit()
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        params = {
            "label": "GenericCreatedFolder",
            "content_type": content_type_list.Folder.slug,
            "parent_id": folder.content_id,
        }
        res = self.testapp.post_json(
            "/api/v2/workspaces/{workspace_id}/contents".format(
                workspace_id=workspace.workspace_id
            ),
            params=params,
            status=403,
        )
        assert isinstance(res.json, dict)
        assert "code" in res.json.keys()
        assert res.json_body["code"] == ErrorCode.INSUFFICIENT_USER_ROLE_IN_WORKSPACE

    def test_api__post_content_create_generic_content__ok_200__try_creating_folder_as_content_manager(
        self
    ) -> None:
        """
        Create generic content but content_type is not allowed in this folder
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.CONTENT_MANAGER, False)
        content_api = ContentApi(current_user=admin, session=dbsession, config=self.app_config)
        folder = content_api.create(
            label="test-folder",
            content_type_slug=content_type_list.Folder.slug,
            workspace=workspace,
            do_save=False,
            do_notify=False,
        )
        content_api.set_allowed_content(folder, [content_type_list.Folder.slug])
        content_api.save(folder)
        transaction.commit()
        self.testapp.authorization = ("Basic", ("test@test.test", "test@test.test"))
        params = {
            "label": "GenericCreatedFolder",
            "content_type": content_type_list.Folder.slug,
            "parent_id": folder.content_id,
        }
        self.testapp.post_json(
            "/api/v2/workspaces/{workspace_id}/contents".format(
                workspace_id=workspace.workspace_id
            ),
            params=params,
            status=200,
        )

    def test_api_put_move_content__err_400__unallowed_sub_content(self):
        """
        move content to a dir where content_type is not allowed
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.CONTENT_MANAGER, False)
        content_api = ContentApi(current_user=admin, session=dbsession, config=self.app_config)
        thread = content_api.create(
            label="test-thread",
            content_type_slug=content_type_list.Thread.slug,
            workspace=workspace,
            do_save=True,
            do_notify=False,
        )
        folder = content_api.create(
            label="test-folder",
            content_type_slug=content_type_list.Folder.slug,
            workspace=workspace,
            do_save=False,
            do_notify=False,
        )
        content_api.set_allowed_content(folder, [])
        content_api.save(folder)
        workspace_id = workspace.workspace_id
        thread_id = thread.content_id
        folder_id = folder.content_id
        transaction.commit()
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {
            "new_parent_id": "{}".format(folder_id),
            "new_workspace_id": "{}".format(workspace_id),
        }
        res = self.testapp.put_json(
            "/api/v2/workspaces/{}/contents/{}/move".format(workspace_id, thread_id),
            params=params,
            status=400,
        )
        assert res.json_body["code"] == ErrorCode.UNALLOWED_SUBCONTENT

    def test_api_put_move_content__ok_200__unallowed_sub_content_renaming(self):
        """
        move content to a dir where content_type is not allowed
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        workspace = workspace_api.create_workspace("test", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, workspace, UserRoleInWorkspace.CONTENT_MANAGER, False)
        content_api = ContentApi(current_user=admin, session=dbsession, config=self.app_config)
        folder = content_api.create(
            label="test-folder",
            content_type_slug=content_type_list.Folder.slug,
            workspace=workspace,
            do_save=True,
            do_notify=False,
        )
        thread = content_api.create(
            label="test-thread",
            content_type_slug=content_type_list.Thread.slug,
            parent=folder,
            workspace=workspace,
            do_save=True,
            do_notify=False,
        )
        with new_revision(session=self.session, tm=transaction.manager, content=folder):
            content_api.set_allowed_content(folder, [])
            content_api.save(folder)
        workspace_id = workspace.workspace_id
        thread_id = thread.content_id
        folder_id = folder.content_id
        transaction.commit()
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {
            "new_parent_id": "{}".format(folder_id),
            "new_workspace_id": "{}".format(workspace_id),
        }
        self.testapp.put_json(
            "/api/v2/workspaces/{}/contents/{}/move".format(workspace_id, thread_id),
            params=params,
            status=200,
        )

    def test_api_put_move_content__ok_200__nominal_case(self):
        """
        Move content
        move Apple_Pie (content_id: 8)
        from Desserts folder(content_id: 3) to Salads subfolder (content_id: 4)
        of workspace Recipes.
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"new_parent_id": "4", "new_workspace_id": "2"}  # Salads
        params_folder1 = {"parent_ids": 3, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        params_folder2 = {"parent_ids": 4, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        folder1_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder1, status=200
        ).json_body
        folder2_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder2, status=200
        ).json_body
        assert [content for content in folder1_contents if content["content_id"] == 8]
        assert not [content for content in folder2_contents if content["content_id"] == 8]
        # TODO - G.M - 2018-06-163 - Check content
        res = self.testapp.put_json(
            "/api/v2/workspaces/2/contents/8/move", params=params, status=200
        )
        new_folder1_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder1, status=200
        ).json_body
        new_folder2_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder2, status=200
        ).json_body
        assert not [content for content in new_folder1_contents if content["content_id"] == 8]
        assert [content for content in new_folder2_contents if content["content_id"] == 8]
        assert res.json_body
        assert res.json_body["parent_id"] == 4
        assert res.json_body["content_id"] == 8
        assert res.json_body["workspace_id"] == 2

    def test_api_put_move_content__ok_200__to_root(self):
        """
        Move content
        move Apple_Pie (content_id: 8)
        from Desserts folder(content_id: 3) to root (content_id: 0)
        of workspace Recipes.
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"new_parent_id": None, "new_workspace_id": 2}  # root
        params_folder1 = {"parent_ids": 3, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        params_folder2 = {"parent_ids": 0, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        folder1_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder1, status=200
        ).json_body
        folder2_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder2, status=200
        ).json_body
        assert [content for content in folder1_contents if content["content_id"] == 8]
        assert not [content for content in folder2_contents if content["content_id"] == 8]
        # TODO - G.M - 2018-06-163 - Check content
        res = self.testapp.put_json(
            "/api/v2/workspaces/2/contents/8/move", params=params, status=200
        )
        new_folder1_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder1, status=200
        ).json_body
        new_folder2_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder2, status=200
        ).json_body
        assert not [content for content in new_folder1_contents if content["content_id"] == 8]
        assert [content for content in new_folder2_contents if content["content_id"] == 8]
        assert res.json_body
        assert res.json_body["parent_id"] is None
        assert res.json_body["content_id"] == 8
        assert res.json_body["workspace_id"] == 2

    def test_api_put_move_content__ok_200__with_workspace_id(self):
        """
        Move content
        move Apple_Pie (content_id: 8)
        from Desserts folder(content_id: 3) to Salads subfolder (content_id: 4)
        of workspace Recipes.
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"new_parent_id": "4", "new_workspace_id": "2"}  # Salads
        params_folder1 = {"parent_ids": 3, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        params_folder2 = {"parent_ids": 4, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        folder1_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder1, status=200
        ).json_body
        folder2_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder2, status=200
        ).json_body
        assert [content for content in folder1_contents if content["content_id"] == 8]
        assert not [content for content in folder2_contents if content["content_id"] == 8]
        # TODO - G.M - 2018-06-163 - Check content
        res = self.testapp.put_json(
            "/api/v2/workspaces/2/contents/8/move", params=params, status=200
        )
        new_folder1_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder1, status=200
        ).json_body
        new_folder2_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder2, status=200
        ).json_body
        assert not [content for content in new_folder1_contents if content["content_id"] == 8]
        assert [content for content in new_folder2_contents if content["content_id"] == 8]
        assert res.json_body
        assert res.json_body["parent_id"] == 4
        assert res.json_body["content_id"] == 8
        assert res.json_body["workspace_id"] == 2

    def test_api_put_move_content__ok_200__to_another_workspace(self):
        """
        Move content
        move Apple_Pie (content_id: 8)
        from Desserts folder(content_id: 3) to Menus subfolder (content_id: 2)
        of workspace Business.
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"new_parent_id": "2", "new_workspace_id": "1"}  # Menus
        params_folder1 = {"parent_ids": 3, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        params_folder2 = {"parent_ids": 2, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        folder1_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder1, status=200
        ).json_body
        folder2_contents = self.testapp.get(
            "/api/v2/workspaces/1/contents", params=params_folder2, status=200
        ).json_body
        assert [content for content in folder1_contents if content["content_id"] == 8]
        assert not [content for content in folder2_contents if content["content_id"] == 8]
        # TODO - G.M - 2018-06-163 - Check content
        res = self.testapp.put_json(
            "/api/v2/workspaces/2/contents/8/move", params=params, status=200
        )
        new_folder1_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder1, status=200
        ).json_body
        new_folder2_contents = self.testapp.get(
            "/api/v2/workspaces/1/contents", params=params_folder2, status=200
        ).json_body
        assert not [content for content in new_folder1_contents if content["content_id"] == 8]
        assert [content for content in new_folder2_contents if content["content_id"] == 8]
        assert res.json_body
        assert res.json_body["parent_id"] == 2
        assert res.json_body["content_id"] == 8
        assert res.json_body["workspace_id"] == 1

    def test_api_put_move_content__ok_200__to_another_workspace_folder_and_subcontents(self):
        """
        correctly move content from projectA_workspace to another projectA_workspace recursively
        move all folder documentation from projectA to projectB projectA_workspace
        - Workspace projectA
          - folder: documentation
            - html-document: report_product_47EA
            - schemas
              - readme.txt
        - Workspace projectB
        :return:
        """
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User).filter(User.email == "admin@admin.admin").one()
        uapi = UserApi(current_user=admin, session=dbsession, config=self.app_config)
        gapi = GroupApi(current_user=admin, session=dbsession, config=self.app_config)
        groups = [gapi.get_one_with_name("users")]
        user = uapi.create_user(
            "test@test.test",
            password="test@test.test",
            do_save=True,
            do_notify=False,
            groups=groups,
        )
        workspace_api = WorkspaceApi(
            current_user=admin, session=dbsession, config=self.app_config, show_deleted=True
        )
        projectA_workspace = workspace_api.create_workspace("projectA", save_now=True)
        projectB_workspace = workspace_api.create_workspace("projectB", save_now=True)
        rapi = RoleApi(current_user=admin, session=dbsession, config=self.app_config)
        rapi.create_one(user, projectA_workspace, UserRoleInWorkspace.CONTENT_MANAGER, False)
        rapi.create_one(user, projectB_workspace, UserRoleInWorkspace.CONTENT_MANAGER, False)
        content_api = ContentApi(current_user=admin, session=dbsession, config=self.app_config)

        documentation_folder = content_api.create(
            label="documentation",
            content_type_slug=content_type_list.Folder.slug,
            workspace=projectA_workspace,
            do_save=True,
            do_notify=False,
        )
        content_api.create(
            content_type_slug=content_type_list.Page.slug,
            workspace=projectA_workspace,
            parent=documentation_folder,
            label="report_product_47EA",
            do_save=True,
            do_notify=False,
        )
        schema_folder = content_api.create(
            label="schemas",
            content_type_slug=content_type_list.Folder.slug,
            workspace=projectA_workspace,
            parent=documentation_folder,
            do_save=True,
            do_notify=False,
        )
        readme_file = content_api.create(
            content_type_slug=content_type_list.File.slug,
            workspace=projectA_workspace,
            parent=schema_folder,
            filename="readme.txt",
            do_save=True,
            do_notify=False,
        )
        with new_revision(session=dbsession, tm=transaction.manager, content=readme_file):
            content_api.update_file_data(
                readme_file, "readme.txt", new_mimetype="plain/text", new_content=b"To be completed"
            )
        transaction.commit()

        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        # verify coherence of workspace content first.
        projectA_workspace_contents = self.testapp.get(
            "/api/v2/workspaces/{}/contents".format(projectA_workspace.workspace_id), status=200
        ).json_body
        assert len(projectA_workspace_contents) == 4
        assert not [
            content
            for content in projectA_workspace_contents
            if content["workspace_id"] != projectA_workspace.workspace_id
        ]
        projectB_workspace_contents = self.testapp.get(
            "/api/v2/workspaces/{}/contents".format(projectB_workspace.workspace_id), status=200
        ).json_body
        assert len(projectB_workspace_contents) == 0
        assert not [
            content
            for content in projectB_workspace_contents
            if content["workspace_id"] != projectB_workspace.workspace_id
        ]

        params = {
            "new_parent_id": None,  # root
            "new_workspace_id": projectB_workspace.workspace_id,
        }
        self.testapp.put_json(
            "/api/v2/workspaces/{}/contents/{}/move".format(
                projectA_workspace.workspace_id, documentation_folder.content_id
            ),
            params=params,
            status=200,
        )

        # verify coherence of workspace after
        projectA_workspace_contents = self.testapp.get(
            "/api/v2/workspaces/{}/contents".format(projectA_workspace.workspace_id), status=200
        ).json_body
        assert len(projectA_workspace_contents) == 0
        assert not [
            content
            for content in projectA_workspace_contents
            if content["workspace_id"] != projectA_workspace.workspace_id
        ]
        projectB_workspace_contents = self.testapp.get(
            "/api/v2/workspaces/{}/contents".format(projectB_workspace.workspace_id), status=200
        ).json_body
        assert len(projectB_workspace_contents) == 4
        assert not [
            content
            for content in projectB_workspace_contents
            if content["workspace_id"] != projectB_workspace.workspace_id
        ]

    def test_api_put_move_content__ok_200__to_another_workspace_root(self):
        """
        Move content
        move Apple_Pie (content_id: 8)
        from Desserts folder(content_id: 3) to root (content_id: 0)
        of workspace Business.
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"new_parent_id": None, "new_workspace_id": "1"}  # root
        params_folder1 = {"parent_ids": 3, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        params_folder2 = {"parent_ids": 0, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        folder1_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder1, status=200
        ).json_body
        folder2_contents = self.testapp.get(
            "/api/v2/workspaces/1/contents", params=params_folder2, status=200
        ).json_body
        assert [content for content in folder1_contents if content["content_id"] == 8]
        assert not [content for content in folder2_contents if content["content_id"] == 8]
        # TODO - G.M - 2018-06-163 - Check content
        res = self.testapp.put_json(
            "/api/v2/workspaces/2/contents/8/move", params=params, status=200
        )
        new_folder1_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_folder1, status=200
        ).json_body
        new_folder2_contents = self.testapp.get(
            "/api/v2/workspaces/1/contents", params=params_folder2, status=200
        ).json_body
        assert not [content for content in new_folder1_contents if content["content_id"] == 8]
        assert [content for content in new_folder2_contents if content["content_id"] == 8]
        assert res.json_body
        assert res.json_body["parent_id"] is None
        assert res.json_body["content_id"] == 8
        assert res.json_body["workspace_id"] == 1

    def test_api_put_move_content__err_400__wrong_workspace_id(self):
        """
        Move content
        move Apple_Pie (content_id: 8)
        from Desserts folder(content_id: 3) to Salads subfolder (content_id: 4)
        of workspace Recipes.
        Workspace_id of parent_id don't match with workspace_id of workspace
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params = {"new_parent_id": "4", "new_workspace_id": "1"}  # Salads
        res = self.testapp.put_json(
            "/api/v2/workspaces/2/contents/8/move", params=params, status=400
        )
        assert res.json_body["code"] == ErrorCode.WORKSPACE_DO_NOT_MATCH

    def test_api_put_delete_content__ok_200__nominal_case(self):
        """
        delete content
        delete Apple_pie ( content_id: 8, parent_id: 3)
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params_active = {"parent_ids": 3, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        params_deleted = {"parent_ids": 3, "show_archived": 0, "show_deleted": 1, "show_active": 0}
        active_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_active, status=200
        ).json_body
        deleted_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_deleted, status=200
        ).json_body
        assert [content for content in active_contents if content["content_id"] == 8]
        assert not [content for content in deleted_contents if content["content_id"] == 8]
        # TODO - G.M - 2018-06-163 - Check content
        self.testapp.put_json(
            # INFO - G.M - 2018-06-163 - delete Apple_Pie
            "/api/v2/workspaces/2/contents/8/trashed",
            status=204,
        )
        new_active_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_active, status=200
        ).json_body
        new_deleted_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_deleted, status=200
        ).json_body
        assert not [content for content in new_active_contents if content["content_id"] == 8]
        assert [content for content in new_deleted_contents if content["content_id"] == 8]

    def test_api_put_archive_content__ok_200__nominal_case(self):
        """
        archive content
        archive Apple_pie ( content_id: 8, parent_id: 3)
        """
        self.testapp.authorization = ("Basic", ("admin@admin.admin", "admin@admin.admin"))
        params_active = {"parent_ids": 3, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        params_archived = {"parent_ids": 3, "show_archived": 1, "show_deleted": 0, "show_active": 0}
        active_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_active, status=200
        ).json_body
        archived_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_archived, status=200
        ).json_body
        assert [content for content in active_contents if content["content_id"] == 8]
        assert not [content for content in archived_contents if content["content_id"] == 8]
        self.testapp.put_json("/api/v2/workspaces/2/contents/8/archived", status=204)
        new_active_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_active, status=200
        ).json_body
        new_archived_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_archived, status=200
        ).json_body
        assert not [content for content in new_active_contents if content["content_id"] == 8]
        assert [content for content in new_archived_contents if content["content_id"] == 8]

    def test_api_put_undelete_content__ok_200__nominal_case(self):
        """
        Undelete content
        undelete Bad_Fruit_Salad ( content_id: 14, parent_id: 10)
        """
        self.testapp.authorization = ("Basic", ("bob@fsf.local", "foobarbaz"))
        params_active = {"parent_ids": 10, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        params_deleted = {"parent_ids": 10, "show_archived": 0, "show_deleted": 1, "show_active": 0}
        active_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_active, status=200
        ).json_body
        deleted_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_deleted, status=200
        ).json_body
        assert not [content for content in active_contents if content["content_id"] == 14]
        assert [content for content in deleted_contents if content["content_id"] == 14]
        self.testapp.put_json("/api/v2/workspaces/2/contents/14/trashed/restore", status=204)
        new_active_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_active, status=200
        ).json_body
        new_deleted_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_deleted, status=200
        ).json_body
        assert [content for content in new_active_contents if content["content_id"] == 14]
        assert not [content for content in new_deleted_contents if content["content_id"] == 14]

    def test_api_put_unarchive_content__ok_200__nominal_case(self):
        """
        unarchive content,
        unarchive Fruit_salads ( content_id: 13, parent_id: 10)
        """
        self.testapp.authorization = ("Basic", ("bob@fsf.local", "foobarbaz"))
        params_active = {"parent_ids": 10, "show_archived": 0, "show_deleted": 0, "show_active": 1}
        params_archived = {
            "parent_ids": 10,
            "show_archived": 1,
            "show_deleted": 0,
            "show_active": 0,
        }
        active_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_active, status=200
        ).json_body
        archived_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_archived, status=200
        ).json_body
        assert not [content for content in active_contents if content["content_id"] == 13]
        assert [content for content in archived_contents if content["content_id"] == 13]
        self.testapp.put_json("/api/v2/workspaces/2/contents/13/archived/restore", status=204)
        new_active_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_active, status=200
        ).json_body
        new_archived_contents = self.testapp.get(
            "/api/v2/workspaces/2/contents", params=params_archived, status=200
        ).json_body
        assert [content for content in new_active_contents if content["content_id"] == 13]
        assert not [content for content in new_archived_contents if content["content_id"] == 13]
