We will develop the stock report capability on this manager application.
This stock report capability is made with the intention to give meanigfull tasks to the workers, We will achive this by obtaining a stock report from the Scanner application, which holds the thresholds of the item types and item properties that should exist on a given zone. 
The Manager application will eventually take the job the Scanner application has, but until then we will develop replicas of some of the models and borrow the Scanner app backend engine.

On this Stock report capability, the requested report will come from the Scanner app as the scanner app is the one that knwos the item placement and the thresholds. But the manager app will handle the workflow of that stock report.


This whole implementation will be only backend driven at the momenet, and this implementation will be a multiphase implementation ( using the agentic flow i have set up ), the idea is to build a strong intention and planning so that the implementation is reliable and the TESTS are align with what the goal is ( there is no need of making over complicated tests that test code modification because the test should only test if the feature works given the data we give, that should simplify the process of building tests substantially  ) . 

The tables that we will need to create for this system to work will be created at /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables on a folder called "stock_report".

Tables:

StockReportItems (IdentityMixin, Base):

- item_type_id : int ( child rel to ItemCategory ( /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/items/item_category.py )  ) 
- item_major_category : string ( enum ItemMajorCategoryEnum ( /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/domain/items/enums.py ) )
- properties : jsonb 
- quantity_requested : int ( for all quantity_* :  >= 0 ( defaults to 0 ))
- quantity_in_queue : int 
- quantity_in_progress : int
- quantity_awaiting : int
- priority : string ( new enum Priority : high, medium, low ( default to null ) )
- priority_order : int ( int order number with in a priority ( default to null ) )
- stock_task_assignments ( parent rel to StockTaskAssignments )
- stock_report_history_records ( parent rel to StockReportHistoryRecords )


StockTaskAssignments (IdentityMixin, Base):
- task_id : int ( fk of Task ( /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/tasks/task.py ))
- item_id : int ( fk of Item ( /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/items/item.py ))
- state : str ( new enum StockTaskAssignmentState: in_queue, in_progress, awating, resolved ( on creation defaults to in_queue) )
- stock_report_item_id ( fk to StockReportItems )

StockReportHistoryRecords (IdentityMixin, Base):
- type: str ( new enum StockReportHistoryType: quantity_requested_change, priority_change, priority_order_change )
- quantity_requested : int 
- quantity_awaiting : int
- priority 
- priority_order 
- created_at : DateTime
- stock_report_item_id ( fk to StockReportItems )


Tables flow and meaning : 

StockReportItems table make up the live projection of the Scanner app stock report and then adding the manager app functionality on top of it. 
What we record from the incoming Scanner app stock report is the incoming itemCategory ( mapped to the item_type_id , this is because im starting to shape the semantics ), the incoming quantityRequested ( mapped to the quantity_requested ), the scanner app itemCategories are the same itemCategories the current manager app holds and this will remaing truth as they are from the same source, so the mapping should be gurantee if the request is legit from the scanner app.  We can also obtain the major category from the  ItemCategory.major_category. We will also store the incoming properties ( mapped to properties ), there can be multiple instances with the same itemCategory but they differ in properties .  

As i mentioned before this table will play the live projection of the Scanner app stock instance on those fields, that means that the Scanner app will constantly update the requested quantity as it changes on the scanne app system, and that is intendend to be reflected in this table. 

The quantity_in_queue is an int value that will represent the live quantity of the items the user has registered as stock_task_assignments and that are in StockTaskAssignments.state= in_queue

The quantity_in_progress is an int value that will represent the live quantity of the items that the user has registered as stock_task_assignements and that are in StockTaskAssignments.state = in_progress

the quantity_awaiting is an int value that will represent the live quantity of the items that the user has registered as stock_task_assignments and that are are in StockTaskAssignments.state = awating

The Scanner app requests will be able to modify ( substract ) the quantity_awaiting, this is because quantity_awating represents the completion of a task item for the manager app perspective, but for the scanner app completion is represented as the item has been placed on the stock instance location, or perhaps in some other location, or perhaps it was sold through the web shop before it even reached to a location. Thus the scanner app notifies the manager app that the item the manager app worked with for fulfilling the stock location instance has now been processed and is no longer awaiting for the manager app, thus -1 from the current quantity_awating. 
As i mentioned before the scanner app can send the request of changing the requested quantity and the awating quantity  at the same time, but it doesn't mean they are directly related, the change in requested quantity is a direct call to the StockReportItems given the itemCategory and the properties match, and the quantity_awating is a quantity change  given that the incoming item.article_number is found as being part of the StockReportItems.StockTaskAssignments and the state of StockTaskAssignments is of awating, it is then that the quantity_awating can change  by the StockTaskAssignments.state having  transtition to resolved.


For the quantity_awating to increase the StockTaskAssignments state must transition to the  state = awating , and this happens when the task state transitions to "ready" or "resolved" . as you can notice the scanner app can decrease this awaiting quantity but manipulating the state of StockTaskAssignments.state only . and the manager app can only manipulate this quantity also by only manipulating the StockTaskAssignments.state only. 

For the quantity_in_progress this is a quantity given the StockTaskAssignments.state= in_progress , and the StockTaskAssignments enters to state = in_progress when the task.state transitions from "pending" to "working" 

For the quantity_in_queue the StockTaskAssignments state should be on state= in_queue , the in_queue state is gain on the StockTaskAssignments at the creation time of a StockTaskAssignments instance, because it is then that an item was found an a task was link to a StockTaskAssignments which linkes direcly to the StockReportItems instance request . a quantity_in_queue can be bigger than the quantity requested for the StockReportItems,  that means,  for fulfilling this StockReportItems type and properties the storage place has more pieces, they just need to be fixed. 

as you can see the quantity_* columns are values that measure a goal and a transition and they can be reconstructed reliably from the state of the objects idepontently, so the key part is to protect the state transitions as they are the source of truth and the counts are a projection of those sources. 



the StockReportHistoryRecords table is a way of keeping history track of specific values of the StockReportItems instances, a stock report history record is made every time a new quantity_registered is registered, given that the new registered quantity_registered is bigger than the previous one. For the quantity_awating this record stores is only additive, meaning it adds for as long as the StockReportItems.quantity_awating keeps increasing ( it doesn't create a new record instance ), but it doesn't add substractions .
The reason for this is because this record goal is to show given a goal how much of it was accomplised before the goal got bigger. you might aks why not smaller? and the answer is because a quantity_requested which gets smaller implies that a fixed funiture piece was placed on the location that was creating the demand thus if we record that in the records we will be counting the meaning of completioin for the scanner app and destroing the initial goal before it was fulfilled. and you might ask why the awaiting quantity is aditive ? and the answer is because awaiting is something that increases justifiably over time, and we don't need to create an instance per addition because we alredy know the completion time for the instance that is getting added through the task.state records . 
The created_at is the time a new instance is created . 
NOTE: i also added the priority and the priority order to this history record, which should create a new instance every time either of those values change, taking the heritage quantiy_* with them. 


Services:

We will need a set of services that handle the state transitions of the StockTaskAssignments as this services will orchestrate the allowed domain transitions given the current state, perform the transition and also perform the quantity change on the linked StockReportItems. Im thinking we will need a service orchestrator for each state transtion and we need atomic functions called with in this services that perform those actions. this services will be used by major services orchestrating other logic or part of backfill / recover scripts . 

We will need create and delete services for StockReportItems, StockTaskAssignments as the creation and deletion of this instances is what the scanner app and the frontend manager app will be capable of manipulating directly, the count transitions is only possible through the workflow.  

On the service in-charge of creating the StockTaksAssignements instance the task and the item must exist and the creation of this instance will default it's  state column to in_queue, but if the provided task is in other state other than pending then it will assign the correct state to that service using the correct domain services for handling that transition. This insance creation will also make the modification to the Task model instance new column is_stock_asssignment ( chaning it's value to true ) . 

we will need a high level service orchestration for managing the StockReportItems instances, so that it first searches if a given StockReportItem instance already exist with the incoming itemCategory and properties, if it does it moves to delegating the operation given it's payload ( change quantity_requested ), or change StockTaskAssignements state instances ( which make the quantity arithmetic ). if it doesn't exist then it creates it accordingly .

For the delete service of StockReportItems this operation is destructive and deletes the linked record history instnaces and the StockTaskAssignments also, on the process of deleting the StockTaskAssignemnts we use the delete service described bellow . 

On the service for deleting a StockTaksAssignements this is straight forward operation, keeping the quantity_* arithmentic accurate and also making the linked Task instances  to change it's column value is_stock_assignment to false . 


We will also have services for changing the StockReportItems priority and priority_order values, this will give the user direct control over the change of the priority and the priority_order . As I mentioned previously the priority_order is a scalar number the user can assigned and it represents the order with in a priority. 
keep in mind that the change of an instance priority automatically assigns that StockReportItem.priority_order to the greatest number + 1 of the current priority_order of that set of the current priorities. Chaning the priority_order with in a priority causes the order recalculation with that priority.  Thus this are two independent services with independent high level endpoints.


Endpoints:

We will create a new family of endpoints for the local manager system at /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/routers/api_v1 on a file called stock_report

We will have an endpoint for creating and deleting a StockReportItem instance 

We will have an endpoint for creating and deleting a or a set of  StockTaskAssignment instances 

We will have an endpoint for changing the StockReportItems.priority 

We will need an endpoint for changing the StockReportItems.priority_order 



For the Scanner app to comunicate with the manager app we will create a endpoint file called location_tracker_webhooks . the endpoints created on that file will use the api key header authentification technique, so the scanner app will need to send the api key on the protected headers for the manager to authentificate it. the manager app will compare the api key to the stored env var MANAGER_API_KEY_TO_LOCATION_TRACKER_APP

we will need a webhook endpoint for receiving the calls from the Scanner app for changing the StockReportItems requested quantity, this endpoint will use the find or create service for handling the request.
the payload shape of this request is:
[{
    itemCategory: str
    properties: { key: value, ... },
    quantityRequested: int 
},...]

We will need a webhook endpoint for receiving the calls from the Scanner app for changing the await state of the found item instances on the StockTaskAssignment. 
Note: previously i mentioned that the scanner app could bring this together, this is no longer true, they are separate concerns and separate incoming calls.

[{
    article_number: str
},...]

As you can see the incoming request from the scanner app only brings the article_number, this is because that is the only thing the scanner app needs to send for the manager app to query and react.






Get endpoints:

We will need also a local family of get endnpoints at the routers/stock_report.py .

We will need a get endpoint for getting the StockReportItems instances. This endpoint will accept query params, priority=string list coma separated ( like priority="high,medium,low" ) when no priority is sent the query service searches for priority=null .  The return list of StockReporetItems is sorted first by priority ( high first, medium after, low last ), and then the priority_order with in each priority state. 
The return shape for each StockReportItems is :
{client_id, quantity_* , priority, priority_order, item_type: { client_id, type_name, major_category }}


We will need a get endpoint for getting the StockTaskAssignments . this endpoint requires a StockReportItem.client_id and it returns:
{ client_id, state, stock_report_item_id, item: serialize_item_compact(item), task: serialize_task_compact( task ) }

the serialize_item_compact and the serialize_task_compact are service serializers that we will create in this implementation which will eventually replace other item and task serializers that currently bring to much info to the frontend for listing ( like the query service get_task /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/queries/tasks/tasks.py, but that transition will happen later ).

the serialize_task_compact will bring the Task: 
client_id, task_type, priority, state, title, return_source, ready_by_at, return_method, created_at, updated_at, clodes_at, completed_at.

the serialize_item_compact will bring the Item:
client_id, article_number, sku, quantity, item_category_snapshot, item_major_category_snapshot, item_images: ( we use the same image serialization technique as the query task service at "item_images": [serialize_image_light(img) for img in item_images], just that now is the internal item compact service which is serializing this images if any ). 

Extra implementations:
As i mention in this text previously we will also add a column to the Task model  ( /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/models/tables/tasks/task.py ) called is_stock_assignment ( which holds a bool value, defaults to false ), this will help me for fast queries later on. 