
we will change how issues in this app are represented, manipulated, stored, and queried.

the intention is:

worker starts the task step that it will be working with and makes it's own list of the issues that it will be correcting, by selecting the issues related to the working section the user is starting the task step and the item. the user will selected the intensity of the issue at the frontend as a number >1 . this issues get store as item issues for the item as a snapshot of the issue type, the intesity, the working section id, the item category id, the step id, the worker id.

in the future for analytics we will use basic arithmetic to figure out the time it takes to take issues types with certain intensity levels. Because we store the total time that it takes to complete a step, over time we can figure out how long it takes to complete a step with certain issue types and intensity levels. This will allow us to give better estimates for how long it will take to complete a step given the issues that are selected at the start of the step.


/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/issue_types/issue_type.py
issue type table continues to store the same information as it currently does.


/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/issue_types/issue_severity.py
issue severity will no longer be needed as the frontend inputed value will take over this role. We will delete this table and all references to it in the codebase.

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/issue_types/issue_category_config.py
issue category config table will no longer be needed.

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/items/item_issue.py
item issue table will have now the following columns:
- client_id
- workspace_id
- item_id
- step_id
- worker_id
- working_section_id
- item_category_id
- issue_type_id
- issue_type_snapshot
- placement_of_issue_snapshot
- intensity
- created_at
- updated_at

adding an issue to an item will need a service that accepts batch adding of item issues, the shape coming from the frontend comes as:
```json
[
  {
    "client_id": "string",
    "item_id": "string",
    "step_id": "string",
    "worker_id": "string",
    "working_section_id": "string",
    "item_category_id": "string",
    "issue_type_id": "string",
    "issue_type_snapshot": "string",
    "placement_of_issue_snapshot": "string",
    "intensity": 1
  },
  // ... more issues
]
```
the issue_type_id can be missing as the user can add it's own custom issue. issue_type_snapshot is always required as it contains the details of the issue type at the time of issue creation, this is important for analytics as we want to know the details of the issue type even if it gets deleted later on.



/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/working_sections/working_section_supported_issue_type.py

the working section supported issues will continue to operate as we will use it to present the options of issues the user can select at the moment of adding the issues to the item. 


/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/items

at the item tables folder we will create a map for issue type to item category:
this table will have same funcionality as the working section supported issues, it will narrow the selection of issues base on category. it will have the following columns:
- client_id
- workspace_id
- item_category_id
- issue_type_id
- placement_of_issue

the placement_of_issue which is a string, will describe the placement of the issue on the item for example: "front left corner", "back right corner", "center", etc... this will help us to have a better understanding of the issues and how to fix them. this will be an optional column as the user can add an issue without specifying the placement of the issue.


the user can remove issues from and item as well, this will require another service that accepts batch removing of item issues, the shape coming from the frontend comes as:
```json
[
  {
    "item_issue_id": "string"
  },
  // ... more issues
]
```

we will need services for creating and linking issues types ( manager / admin configuration ). this services will allow to create issue types and link them to working sections and item categories. the shape of the request coming from the frontend will be:
```json
{
    "issue_type_name": "string",
    "linked_working_section_ids": ["string"],
    "linked_item_category_ids": [
        {
            "item_category_id": "string",
            "placement_of_issue": "string"
        }
    ],
}
```
this service will create an issue type and link it to the working sections and item categories provided in the request. the placement_of_issue is a string that describes the placement of the issue on the item and it is placed at the item category issue instance that gets created when creating the item category to issue type link. this is because the same issue type can have different placements for different item categories. for example, a "scratch" issue type can have a placement of "front left corner" for a "table" item category and a placement of "center" for a "chair" item category. this will allow us to have a better understanding of the issues and how to fix them.

we need a service that allows the user to edit the issue type and it's linkage to the working sections and item categories. this service will allow to edit the issue type name, the linked working sections and the linked item categories. the shape of the request coming from the frontend will be:
```json
{
    "issue_type_id": "string",
    "issue_type_name": "string",
    "linked_working_section_ids": ["string"],
    "linked_item_category_ids": [
        {
            "item_category_id": "string",
            "placement_of_issue": "string"
        }
    ],
}
```
this service will edit the issue type and update its linkage to the working sections and item categories based on the request. 


we will need a service that allows the user to delete an issue type. this service will delete the issue type and all its linkages to working sections and item categories. the shape of the request coming from the frontend will be:
```json
[{
    "issue_type_id": "string"
}]
```
this service will delete the issue type and all its linkages to working sections and item categories based on the request. when an issue type gets deleted, the existing item issues that are linked to this issue type will not be deleted as we want to keep the history of the issues for analytics purposes, but they will have their issue_type_id set to null and they will keep the issue_type_snapshot which contains the details of the issue type at the time of issue creation. this way we can still have the details of the issue type for analytics even if the issue type gets deleted later on.


current services that will be removed to allow for this new way of handling issues:

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/commands/items/create_item_issue.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/commands/items/delete_item_issue.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/commands/items/delete_item_issues.py



creating an item will have a call to the service for creating the item issues, if item issues are send on the creation of an item: 
/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/commands/items/create_item.py

same goes for the creation of a task:

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/commands/tasks/create_task.py


for the item issue serializer: 
/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/domain/items/serializers.py
we will change the serializer serialize_item_issue so that it now return the the new shape of item isssues:
- client_id
- workspace_id
- item_id
- step_id
- worker_id
- working_section_id
- item_category_id
- issue_type_id
- issue_type_snapshot
- placement_of_issue_snapshot
- intensity
- created_at
- updated_at



we will create a router for obtaining the item issues given an item id, this will be used for the frontend to obtain the issues of an item when starting a step. the endpoint will be:
GET /api/v1/items/{item_id}/issues


this endpoint will allow for query params for filtering the issues.
this query service will be located at:
 /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/queries/items/get_item_issues.py

 and it will allow for "q" param look at how we handle this param in /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/queries/items/items.py . 

that "q" when present it will use the string query utility to search on columns: issue_type_snapshot, placement_of_issue_snapshot. this will allow the frontend to search for issues by their type and placement when starting a step.

for filtration it will take params:
- working_section_id
- item_category_id
- issue_type_id


I will like you to create an implementation plan for this new way of handling issues.
the plan will be implemented by codex.

