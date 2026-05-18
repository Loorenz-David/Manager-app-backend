the task system is the main core of the whole application
as the whole application is based on creating task and assign them to workstations. 
users get their tasks through task steps and change the state of those steps, we record the time of the task step state movements.

the whole though flow is as follows:

users that are sellers, managers admins can create tasks, assigning an item, issues and upholstery, plus the other task fields, the seller only creates task that are not assigned to any working station.

users that are managers can take a created task and ssign it to a working station, and also can create a task and assign it directly to a working station, the manager can also update the task fields and assign or unassign item, issues and upholstery. 

a task that has no assigned working station gains the state pending, when assigning a task to any working station the task gains the state assigned, when any of the assigned working steps starts working the task gains the state working, when all the assigned task steps are finished the task gains the state ready, a manager, seller or admin can then mark a task to state resolved, meaning the task is fully completed, it was either given to the costumer or taken to be sold at the shop. the resolved state is a terminal state that can be placed at any point of the task process, so as the failed, and cancelled states. stalled is a state that i have not yet though on how it will be triggered.

users that are workers can only update the state of the task steps and record time, they can not update any other field of the task or assign or unassign item, or upholstery, they can however update the issues of an item. a worker will constantly change the state of a task step working -> paused, or working -> ended_shift, or working -> completed, paused -> working, paused -> ended_shift. when a task step is created it first gains the state pending, then it can transition from pending -> working. the blocked state will be used for the dependencies, the task step readines will be used for the dependencie state of the task, when the dependencies are not ready the task step gains the readiness_status blocked, when one or more dependencies are ready the task step gains the readiness_status -> partial, when all the dependencies are ready the task step gains the readiness_status -> ready, task that don't have dependenies on creation gain the readiness_status ready. i will have other comamnds that transision other instances state mark task steps readiness_status to block or ready, this higer commands will use an interface command to change that state that is not conflictive with the current dependencies transition state logic, meaning that the dependency rules over the external ones but when ready the external interaction can change that readiness_status state, for example: this readiness_status will be used for for the upholstery need:
when an item upholstery need gains the state needs_ordering, missing_quantity, ordered, failed the readiness_status gains the readiness_status of blocked,  whe the need of an upholstery gets the state available the readiness_status gains the state ready, this two processes manipulate the same column readiness_status and should not conflict. 
when changing the state of a task step to working or pause there will be other side effects depending on the working section, i will place those side effects in a way that i can expand easily orginized and scalable the side effects ( commands to call ). 

changing the state of a task step will always create a StepStateRecord placing the state and the reason, reasons are mapped to the enums . a task step always has a direct access to the last state record through latest_state_record_id . it is through the StepStateRecord that we record the time of each state, start and end. User sees a task in pending, starts working a task step changes the state to working and a StepStateRecord is created with state working and start time marked, accuracy 100 , then the user goes for lunch and pauses the task step, this maks the task step state to paused and the latest_state_record_id currently with no end time ( working ) marks the end time, then it creates a new record with paused state recording the reason and the start time, the user comes back from lunch and starts working again, this marks the task step state to working, then the latest_state_record_id with paused state and no end time marks the end time and creates a new record with working state and start time marked, the user finishes the task step and marks it as completed, this marks the task step state to completed and the latest_state_record_id with working state and no end time marks the end time and creates a new record with completed state and start time marked.

marking end times on state records records updates the other stats tables: UserDailyWorkStats,UserLifetimeStats,UserSectionDailyWorkStats, WorkingSectionDailyWorkStats. this process is passed to a worker to be done asynchonously to avoid performance issues, but the marking of the end time and the creation of the new state record is done in a transaction to avoid inconsistencies in the data. each table will have it's own atomic commands to update the stats, we can create context classes to pass the data to those commands.





the incoming task can have costumer as null meaning no costumer will be linked nor created to the task. when costumer is present we use the create or link command that already exist for costumer, but the incoming costumer data is used on the snapshot on the task. missing values can be filled by the linked costumer. 

task priority is used to order the tasks in the working station, the higher the priority the sooner it should be taken by the worker, 


a task can gain more task steps after being created, or they can be removed. 


total_dependencies and completed_dependencies are used to calculate the readiness status of the task step, if total_dependencies is 0 then the task step is ready, if total_dependencies is greater than 0 and completed_dependencies is equal to total_dependencies then the task step is ready, if total_dependencies is greater than 0 and completed_dependencies is less than total_dependencies then the task step is not ready. this calculation will run when a task step that has dependendents on top is marked as completed, this will mark the dependents task steps as ready or partial if the dependencies are met.

recorded_time_marked_wrong is meant to represent when a user has marked wrong start end states, for instance it started a task step and forgot to pause it when it went for lunch, thus at the frontend the user can send the time is not accurate, thus the system should mark that, that record will notbe used for metrics calculations but it will be useful for the managers to see when the time recorded is not accurate and take that into account when making decisions based on the metrics. when that happnes the system should take the average time on other similar task steps to calculate the metrics, this is to avoid that the metrics are affected by wrong time recordings, when that happnes we record that at taken_from_average, so the time is still recorded on the metrics but taken from the average of other similar task steps. 



quering and returning the task list:

this query command will support the query "q" utility, the string columns that it queries against are: title, additional_details, *_phone_number, *_email, item.article_number, item.sku, item.designer, item.position, item.category_snapshot, item.major_category_snapshot, ItemUpholstery.name, ItemUpholstery.code. 

then it has the filters for:
working station, the filter can come as a list of working station names, the query will return tasks that are assigned to any of the working stations in the list.

task state, the filter can come as a list of task states, the query will return tasks that are in any of the states in the list.

task step state, the filter can come as a list of task step states, the query will return tasks that have any task step in any of the states in the list.

task step readiness_status, the filter can come as a list of readiness_status, the query will return tasks that have any task step with any of the readiness_status in the list.

task priority, the filter can come as a list of task priorities, the query will return tasks that have any of the priorities in the list.


task type, the filter can come as a list of task types, the query will return tasks that have any of the types in the list.

task return_source , the filter can come as a list of task return sources, the query will return tasks that have any of the return sources in the list.

task ready_by_date, the filter can come as a date range, the query will return tasks that have a ready_by_date within the date range. that range comes in separate keys ready_from_date and ready_to_date. ready_from_date -> ready_to_date if no ready_to_date then infinity, if no ready_from_date then -infinity -> ready_to_date. 

task scheduled_start_at and scheduled_end_at, the filter can come as a date range, the query will return tasks that have a scheduled_date within the date range. that range comes in separate keys scheduled_from_date and scheduled_to_date. scheduled_from_date -> scheduled_to_date if no scheduled_to_date then infinity, if no scheduled_from_date then -infinity -> scheduled_to_date.


upholstery requirements filter, the filter can come as list of states  which checks agains the ItemUpholsteryRequirement.state,


deleted_at filter, the filter can come as a boolean, if true the query will return tasks that have deleted_at not null, if false the query will return tasks that have deleted_at null. this is to support the soft delete of tasks. as default when no deleted_at filter is provided the query will return tasks that have deleted_at null, meaning only the non deleted tasks.


the query command we use the current stablish pagination.

the first compress shape for the task list will be a serializer which returns: [ {
    task: {id, task_type, priority, state, title, summary, return_source, item_location, ready_by_at, scheduled_start_at, scheduled_end_at, return_method, fulfillment_method},

item: { id, article_number, quantity, sku, designer, position, category_snapshot, major_category_snapshot, external_id, external_source, external_order_id, task_id },

item_upholstery: { id, name, code, amount_meters, source, item_id, task_id },

item_upholstery_requirements: [{ id, upholstery_inventory_id,  amoutn_meters, state, ordered_at, task_id, item_upholstery_id }],

task_steps:[{ id, state, readiness_status, working_section_id, working_section_snapshot, assigned_worker_id, assigned_worker_display_name_snapshot, created_at, task_id, total_dependencies, completed_dependencies}],
}
]

the task are default to be orderd by ready_by_at at the top, then by priority, then by created_at. the user can change the order by any of those fields or any other field by passing an order_by parameter with the field name and the order direction (asc or desc) for example order_by=ready_by_at:asc,priority:desc,created_at:asc. if no order direction is provided it defaults to asc.



known tables:
/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/tasks/README.md

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/tasks/task.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/tasks/task_step.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/tasks/task_step_dependency.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/tasks/task_step_assignment_record.py


/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/tasks/task_item.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/tasks/step_state_record.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/items/item.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/items/item_upholstery.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/items/item_upholstery_requirement.py


/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/analytics/user_daily_work_stats.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/analytics/user_lifetime_stats.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/analytics/user_section_daily_work_stats.py


/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/analytics/working_section_daily_work_stats.py

kwnon commands:

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/commands/customers/find_or_create_customer.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/commands/items/create_item.py

/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/queries/utils/string_filter.py



