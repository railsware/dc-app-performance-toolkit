from locustio.common_utils import init_logger, jira_measure, run_as_specific_user  # noqa F401
from locustio.jira.http_actions import create_template, fetch_templates, fetch_last_template_usage, apply_template
from locustio.jira.requests_params import jira_datasets
import random
from time import sleep

logger = init_logger(app_type='jira')
jira_dataset = jira_datasets()


@jira_measure("locust_app_specific_action:create_template")
# @run_as_specific_user(username='admin', password='admin')  # run as specific user
def app_specific_action(locust):
    create_template(locust)


@run_as_specific_user(username='admin', password='admin')
def app_specific_action_2(locust):

    @jira_measure("locust_app_specific_action:fetch_and_apply_template")
    def fetch_and_apply_template():
        template_ids = fetch_templates(locust)
        id = random.choice(template_ids)
        apply_template(locust, id)
        return id

    template_id = fetch_and_apply_template()

    @jira_measure("locust_app_specific_action:issues_creation")
    def wait_for_application(max_iterations=100):
        iterations = 0
        while iterations < max_iterations:
            sleep(1)
            progress = fetch_last_template_usage(locust, template_id)
            if progress == '100':
                break
            iterations += 1
        else:
            logger.error("Error fetching template usages")

    wait_for_application()




