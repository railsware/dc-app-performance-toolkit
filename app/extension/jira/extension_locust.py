import random
import re
from locustio.common_utils import init_logger, jira_measure, generate_random_string, TEXT_HEADERS
from locustio.jira.requests_params import jira_datasets

logger = init_logger(app_type='jira')
jira_dataset = jira_datasets()
# Smart Checklist app configuration
status_ids = [1, 2, 3, 4]

@jira_measure("locust_app_specific_action")
def app_specific_action(locust):
    # update locustio.jira.requests_params with 'data_sets["custom-issues"] = read_input_file (JIRA_DATASET_CUSTOM_ISSUES)'
    # issue_key = random.choice(jira_dataset["custom-issues"])[0]
    # hardcode issue keys as custom-issues dataset is not available here somehow
    issue_key=random.choice(["CP-1", "CP-2", "CP-3", "CP-4", "CP-5", "CP-6", "CP-7", "CP-8", "CP-9", "CP-10"])

    logger.locust_info(f"Get associated checklists from {issue_key}")
    CHECKLIST_PARAMS = {
        "issueKey": issue_key
    }
    #1
    checklist_request = locust.get("/rest/railsware/1.0/checklist", params=CHECKLIST_PARAMS,catch_response=True)
    checklist_content = checklist_request.content.decode("utf-8")
    if "checklists" not in checklist_content:
        logger.error(f"'checklists' was not found in {checklist_content}")
    checklist_id_pattern = '"checklistId":(.[0-9]+)'
    checklist_ids = re.findall(checklist_id_pattern, checklist_content)
    if len(checklist_ids) > 0:
        checklist_id = checklist_ids[0]
        logger.locust_info(f"Check list id: {checklist_id}")
        item_id_pattern = '"id":([0-9]+)'
        item_ids = re.findall(item_id_pattern, checklist_content)
        TEXT_HEADERS["Content-Type"] = "application/json"
        label = generate_random_string(20, only_letters=True)
        if len(item_ids) > 0:
            item_id = item_ids[0]
            logger.locust_info(f"Item id: {item_id}")
            logger.locust_info(f"Updating checklist item in {issue_key}")
            status_id = random.choice(status_ids)
            update_checklist_body = []
            item_for_update = {
                "id": item_id,
                "label": label,
                "rank": 1,
                "status": {
                    "id": status_id
                }
            }
            update_checklist_body.append(item_for_update)
            #2
            update_item_request = locust.client.request(method="PUT", url=f"/rest/railsware/1.0/checklist/{checklist_id}", json=update_checklist_body, headers=TEXT_HEADERS, catch_response=True)
            update_item_content = update_item_request.content.decode("utf-8")
            if label not in update_item_content:
                logger.error(f"Label {label} was not found in {update_item_content}")
        else:
            logger.locust_info(f"Creating checklist item in {issue_key}")
            #3
            label = "- " + label
            item_body = {
                "isReplace": "false",
                "stringValue": label
            }
            create_item_request = locust.client.request(method="PUT", url=f"/rest/railsware/1.0/checklist/{checklist_id}/item", json=item_body, headers=TEXT_HEADERS, catch_response=True)
            create_item_content = create_item_request.content.decode("utf-8")
            if "checklists" not in create_item_content:
                logger.error(f"'checklists' was not found in {create_item_content}")