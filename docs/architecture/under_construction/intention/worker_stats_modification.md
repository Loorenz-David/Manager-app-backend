we will now implement one more router and service for obtianing stats. 
/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/routers/api_v1/worker_stats.py

The objective is to be able to pass a target user who is part of those task steps states records. 

and it will return an object like the query service list_tasks ( /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/queries/tasks/tasks.py ) return with some extra values. the values it will return similar to the list_tasks are task, primary_item and item_images. 

the service aims to return each task the user was involve into the current date given the task steps the user interacted with ( can be provided by the frontend and it fallsback to current utc time if not provided ). 

so for instance if target user completed 3 task steps, 

