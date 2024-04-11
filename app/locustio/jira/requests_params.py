from locustio.common_utils import generate_random_string, read_input_file, BaseResource
from util.project_paths import JIRA_DATASET_ISSUES, JIRA_DATASET_JQLS, JIRA_DATASET_KANBAN_BOARDS, \
    JIRA_DATASET_PROJECTS, JIRA_DATASET_SCRUM_BOARDS, JIRA_DATASET_USERS
from extension.jira.constants import PROJECT_ID, EPIC_ID, ISSUE_TYPE_IDS, SUB_TASK_ID, PRIORITY_IDS, ADMIN_USER_KEY
import json
import uuid
import random


def jira_datasets():
    data_sets = dict()
    data_sets["issues"] = read_input_file(JIRA_DATASET_ISSUES)
    data_sets["users"] = read_input_file(JIRA_DATASET_USERS)
    data_sets["jqls"] = read_input_file(JIRA_DATASET_JQLS)
    data_sets["scrum_boards"] = read_input_file(JIRA_DATASET_SCRUM_BOARDS)
    data_sets["kanban_boards"] = read_input_file(JIRA_DATASET_KANBAN_BOARDS)
    data_sets["projects"] = read_input_file(JIRA_DATASET_PROJECTS)
    page_size = 25
    projects_count = len(data_sets['projects'])
    data_sets['pages'] = projects_count // page_size if projects_count % page_size == 0 \
        else projects_count // page_size + 1
    return data_sets


class JiraResource(BaseResource):

    def __init__(self, resource_file='locustio/jira/resources.json'):
        super().__init__(resource_file)


class Login(JiraResource):
    action_name = 'login_and_view_dashboard'
    atl_token_pattern = r'name="atlassian-token" content="(.+?)">'

    login_body = {
        'os_username': '',
        'os_password': '',
        'os_destination': '',
        'os_cookie': True,
        'user_role': '',
        'atl_token': '',
        'login': 'Log in'
    }


class BrowseIssue(JiraResource):
    action_name = "view_issue"
    issue_id_pattern = r'id="key-val" rel="(.+?)">'
    project_avatar_id_pattern = r'projectavatar\?avatarId\=(.+?)" '
    edit_allow_pattern = "secure\/EditLabels\!default"  # noqa W605
    browse_project_payload = {"id": "com.atlassian.jira.jira-projects-issue-navigator:sidebar-issue-navigator"}


class ViewDashboard(JiraResource):
    action_name = 'view_dashboard'


class CreateTemplate(JiraResource):
    id_pattern = '"id":([0-9]+)'

    @staticmethod
    def _generate_node(issue_hierarchy_level, issue_type_id, parent_id=None):
        node_id = str(uuid.uuid4())
        summary = f"Issue {str(random.randint(1, 100))}"
        description = f"{generate_random_string(200)}"
        fields = {
            "priority": {
                "id": random.choice(PRIORITY_IDS)
            }
        }
        node_data = {
            "id": node_id,
            "summary": summary,
            "description": description,
            "issueTypeId": issue_type_id,
            "issueHierarchyLevel": issue_hierarchy_level,
            "fields": json.dumps(fields)
        }
        if parent_id is not None:
            node_data["parentId"] = parent_id
        return node_data

    def _generate_nodes_hierarchy(self):
        epic = self._generate_node("Epic", EPIC_ID)
        num_of_stories = 5
        nodes = [epic]

        for _ in range(num_of_stories):
            issue_type_id = random.choice(ISSUE_TYPE_IDS)
            node = self._generate_node("Story", issue_type_id, epic["id"])
            nodes.append(node)
            nodes.append(self._generate_node("Subtask", SUB_TASK_ID, node["id"]))
        return nodes

    def prepare_graqhql_body(self):
        operation_name = "createTemplateFromNodes"
        query = "mutation createTemplateFromNodes($input: CreateTemplateFromNodesInput!) {\n  createTemplateFromNodes(input: $input) {\n    template {\n      id\n      name\n      nodes {\n        ...TemplateNode\n        __typename\n      }\n      variables {\n        name\n        type\n        __typename\n      }\n      __typename\n    }\n    validations {\n      validationErrors\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment TemplateBasicNode on TemplateNode {\n  checklist\n  id\n  level\n  parentId\n  position\n  summary\n  issueTypeId\n  __typename\n}\n\nfragment TemplateNode on TemplateNode {\n  ...TemplateBasicNode\n  description\n  fields\n  __typename\n}"
        template_name = f"Locust template name {generate_random_string(20)}"

        nodes = self._generate_nodes_hierarchy()
        body = {
            "operationName": operation_name,
            "query": query,
            "variables": {
                "input": {
                    "name": template_name,
                    "nodes": nodes,
                    "projectId": PROJECT_ID,
                    "variables": []
                }
            }
        }
        return body


class FetchTemplates(JiraResource):
    id_pattern = '"id":([0-9]+)'

    def prepare_graqhql_body(self):
        operation_name = "templatesList"
        query = "query templatesList($projectIds: [Long!]) {\n  templates(projectIds: $projectIds) {\n    id\n    name\n    __typename\n  }\n}"

        body = {
            "operationName": operation_name,
            "query": query,
            "variables": {
                "projectIds": [PROJECT_ID]
            }
        }
        return body


class ApplyTemplate(JiraResource):
    id_pattern = '"id":([0-9]+)'

    def prepare_graqhql_body(self, template_id):
        operation_name = "applyTemplate"
        query = "mutation applyTemplate($id: Long!, $variables: [VariableValueInput!]) {\n  applyTemplate(id: $id, variables: $variables) {\n    template {\n      id\n      __typename\n    }\n    validations {\n      isValid\n      validationErrors\n      __typename\n    }\n    __typename\n  }\n}"

        body = {
            "operationName": operation_name,
            "query": query,
            "variables": {
                "id": template_id,
                "variables": []
            }
        }
        return body


class FetchLastTemplateUsage(JiraResource):
    progress_pattern = '"progress":\s*([0-9]+)'

    def prepare_graqhql_body(self, template_id):
        operation_name = "templateUsage"
        query = "query templateUsage($id: Long!, $userId: String!) {\n  templates(ids: [$id]) {\n    id\n    name\n    usages(last: 1, userId: $userId) {\n      id\n      status\n      progress\n      rootIssueKey\n      __typename\n    }\n    __typename\n  }\n}"

        body = {
            "operationName": operation_name,
            "query": query,
            "variables": {
                "id": template_id,
                "userId": ADMIN_USER_KEY
            }
        }
        return body


class CreateIssue(JiraResource):
    action_name = 'create_issue'
    atl_token_pattern = '"atl_token":"(.+?)"'
    form_token_pattern = '"formToken":"(.+?)"'
    issue_type_pattern = '\{&quot;label&quot;:&quot;Story&quot;,&quot;value&quot;:&quot;([0-9]*)&quot;'  # noqa W605
    project_id_pattern = r'class=\\"project-field\\" value=\\"(.+?)\\"'
    resolution_done_pattern = r'<option value=\\"([0-9]*)\\">\\n            Done\\n'
    fields_to_retain_pattern = '"id":"([a-z]*)","label":"[A-Za-z0-9\- ]*","required":(false|true),'  # noqa W605
    custom_fields_to_retain_pattern = '"id":"customfield_([0-9]*)","label":"[A-Za-z0-9\- ]*","required":(false|true),'  # noqa W605
    user_preferences_payload = {"useQuickForm": False,
                                "fields": ["summary", "description", "priority", "versions", "components"],
                                "showWelcomeScreen": True}
    create_issue_key_pattern = '"issueKey":"(.+?)"'
    err_message_create_issue = 'Issue was not created'

    @staticmethod
    def prepare_issue_body(issue_body_dict: dict, user):
        description = f"Locust description {generate_random_string(20)}"
        summary = f"Locust summary {generate_random_string(10)}"
        environment = f'Locust environment {generate_random_string(10)}'
        duedate = ""
        reporter = user
        timetracking_originalestimate = ""
        timetracking_remainingestimate = ""
        is_create_issue = "true"
        has_work_started = ""
        project_id = issue_body_dict['project_id']
        atl_token = issue_body_dict['atl_token']
        form_token = issue_body_dict['form_token']
        issue_type = issue_body_dict['issue_type']
        resolution_done = issue_body_dict['resolution_done']
        resolution_string = f'&resolution={resolution_done}' if resolution_done else ''
        fields_to_retain = issue_body_dict['fields_to_retain']
        custom_fields_to_retain = issue_body_dict['custom_fields_to_retain']

        request_body = f"pid={project_id}&issuetype={issue_type}&atl_token={atl_token}&formToken={form_token}" \
                       f"&summary={summary}&duedate={duedate}&reporter={reporter}&environment={environment}" \
                       f"&description={description}&timetracking_originalestimate={timetracking_originalestimate}" \
                       f"&timetracking_remainingestimate={timetracking_remainingestimate}" \
                       f"&is_create_issue={is_create_issue}" \
                       f"&hasWorkStarted={has_work_started}{resolution_string}"
        fields_to_retain_body = ''
        custom_fields_to_retain_body = ''
        for field in fields_to_retain:
            fields_to_retain_body = fields_to_retain_body + 'fieldsToRetain=' + field[0] + '&'
        for custom_field in custom_fields_to_retain:
            custom_fields_to_retain_body = custom_fields_to_retain_body + 'fieldsToRetain=customfield_' \
                                           + custom_field[0] + '&'
        custom_fields_to_retain_body = custom_fields_to_retain_body[:-1]  # remove last &
        request_body = request_body + f"&{fields_to_retain_body}{custom_fields_to_retain_body}"
        return request_body


class SearchJql(JiraResource):
    action_name = 'search_jql'
    issue_table_payload = {"startIndex": "0",
                           "jql": "order by created DESC",
                           "layoutKey": "split-view",
                           "filterId": "-4"}
    ids_pattern = '"issueIds":\[([0-9\, ]*)\]'  # noqa W605
    issue_key_pattern = '\"table\"\:\[\{\"id\"\:(.+?)\,\"key\"\:\"(.+?)\"'  # noqa W605
    issue_id_pattern = '\"table\"\:\[\{\"id\"\:(.+?)\,'  # noqa W605
    edit_allow_string = 'secure/EditLabels!default'

    @staticmethod
    def prepare_jql_body(issue_ids):
        request_body = "layoutKey=split-view"
        issue_ids = issue_ids[0].split(',')
        for issue_id in issue_ids:
            request_body = request_body + '&id=' + issue_id
        return request_body


class ViewProjectSummary(JiraResource):
    action_name = 'view_project_summary'
    err_message = 'Project not found'


class EditIssue(JiraResource):
    action_name = 'edit_issue'
    issue_type_pattern = 'name="issuetype" type="hidden" value="(.+?)"'
    atl_token_pattern = 'atl_token=(.+?)"'
    issue_priority_pattern = 'selected="selected" data-icon="(.+?)" value="(.+?)">'
    issue_assigneee_reporter_pattern = '<select id="assignee" (.+?)Automatic</option><option value="(.+?)" ' \
                                       '(.+?)<option selected="selected" value="(.+?)"'
    issue_reporter_pattern = 'assignee.*<option selected="selected" value="(.+?)"'
    last_visited_body = {"id": "com.atlassian.jira.jira-projects-issue-navigator:sidebar-issue-navigator"}
    err_message_issue_not_found = 'Issue not found'


class AddComment(JiraResource):
    action_name = 'add_comment'
    form_token_pattern = 'name="formToken"\s*type="hidden"\s*value="(.+?)"'  # noqa W605
    atl_token_pattern = r'name="atlassian-token" content="(.+?)">'
    browse_project_payload = {"id": "com.atlassian.jira.jira-projects-issue-navigator:sidebar-issue-navigator"}


class BrowseProjects(JiraResource):
    action_name = 'browse_projects'


class ViewBoard(JiraResource):

    def __init__(self, action_name):
        self.action_name = action_name
        super().__init__()

    project_key_pattern = '\["project-key"\]=\"\\\\"(.+?)\\\\""'  # noqa W605
    project_id_pattern = '\["project-id"\]=\"(.+?)\"'  # noqa W605
    project_plan_pattern = 'com.pyxis.greenhopper.jira:project-sidebar-(.+?)-(.+?)"'


class BrowseBoards(JiraResource):
    action_name = 'browse_boards'
