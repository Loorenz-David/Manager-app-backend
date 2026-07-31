Currently i have a table / model called TaskStepAcknowledgment ( /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/tasks/task_step_acknowledgment.py ). instances for this table are created when some task step is reassigned to a new user at add_task_steps ( /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/commands/task_steps/add_task_steps.py ) . 

The frontend will now have a page where the user will be able to see all the task steps that have been reassigned to them. To facilitate this, we need to create an endpoint that retrieves all TaskStepAcknowledgment instances for the currently logged-in user, where the user has the working section assigned to that reassigned task step.
Where the task step is not completed yet. 
We can use a join queries to achieve this effectively.


We will need to create an endpint for getting the counts of the re-assigned task steps also, the service for this endpoint is light and fast as it is only focus on returning the counts.

when serializing task steps for the re-assigned task steps we should use the same response object as the list_working_section_steps uses ( /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/queries/working_sections/list_working_section_steps.py ). 
One thing to add is that we will be returning the working working sections objects in a separate dict for the frontend to build the contianers matching task steps and working sections. 

I will like you to create an implementation plan for this endpoint and services it will use using the template plan ( /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/docs/architecture/under_construction/implementation/TEMPLATE_PLAN.md ) , use the contract guide /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/task_system/backend_contract_goal_mapping_guide.md for aligning the implementation with the backend contract goals. Another Claude session will be implementing this plan.

After the implementation, the agent should also generate a handoff at /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/docs/handoff/to_frontend for the frontend team to consume the endpoint. The handoff should include the endpoint URL, request parameters, response format ( detailed serialization for the frontend to build the schema ).
 

