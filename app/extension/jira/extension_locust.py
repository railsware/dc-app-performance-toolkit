from locustio.common_utils import init_logger, jira_measure, run_as_specific_user  # noqa F401
from locustio.jira.http_actions import create_template

logger = init_logger(app_type='jira')
jira_dataset = jira_datasets()


@jira_measure("locust_app_specific_action")
# @run_as_specific_user(username='admin', password='admin')  # run as specific user
def  app_specific_action(locust):
    create_template(locust)
