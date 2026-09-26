Currently the stock report system is a live stock report of the requested quantities given the external service which provides the stock rules and the stock instances ( scanner appliacation ). 

We will modify this so that it still remains live but for the manager application consumers it is a snapshot system, so that the manager and progress create "versions"/"snapshots" of a stock report.

This is made for two reasons:
1. workers will have a stable idea of progress as requeseted quantity changes.
2. managers can re-organize the priorities every x amount of days given the consumption ( requested amount ), and seen progress of workers fullfilling the stock instances.

The reason why i say it remain live is because the current live system holds the true copy of the external service providing this stock instances, and what needs to be snapshoted is values of the live copy, and the live copy will act as a mirror image of the original given the changes on the values that can change.

a snapshot of a stock instance holds the following columns:
* stock_report_item_id ( fk to StockReportItem )
* quantity_requested ( int )
* quantity_in_queue ( int )
* quantity_in_progress ( int )
* quantity_awating  ( int )
* quantity_missing ( int )
* priority ( StockReportPriorityEnum )
* priority_order ( int )
* active_at: DateTime  ( default current creation time )
* closed_at: DateTime | null 
* created_at: DateTime ( default current creation time )

The snapshot is considered active when active_at = some date and time which is < current time  and closed_at is null 

Only one snapshot is allowed to be active at the time, if a new one gets created it automatically closes the previous active one ( atomicity transaction ) .

When creating a snapshot we are taking the targeted StockReportItem and getting the current quantity_requested, quantity_in_queue, quantity_in_progress, quantity_awaiting

The quantity_requested is the value that is set in "stone" from the snapshot, as that is what we are actually snapshoting.

The other quantity_* values are reflection of the StockReportItem quantiy_* system changes, that is what i mean it is an active reflection of the StockReportItem system in some quantity_* values, those being ( quantity_in_queue, quantity_in_progress, quantity_awating ).

We will remove the "priority" and "priority_order" columns from the StockReportItem, this is because it will now be the snapshot which holds those values, this is because every time a new snapshot is created the manager has the obligation to reassign the priority and the priority_order ( keeping them active an aware of the current situation ). But we will have an endpoint / service which will allow the user to pick a previous snapshot priority and priority order ( for a set of snapshots i mean ). 

the new column quantity_missing is a value which also belongs to the snapshot, and it is a value which will play the role of marking missing items from the inventory so that they are substracted from the current requested quantity so that they don't disturb to the worker the undertstanding of what it should be fixing ( or finding ), and for the manager to also ignore ir or acknowledge it, meaning we can have a special query filter or a new query endpoint which allows to get all the stock report items which have an active snapshot with > 0 missing items, so that the person who buys furniture can undertand what it should be looking for. 

so as you can see this is a relatively easy change, but that it must be done correctly.
For what changes to the frontend is not that much also, the frontend continues to use the same endpoints for re-organizing the stock report item intance but we are changing the priority or the priority order of the active snapshot. 

when the frontend requests stock report items it only gets the once that have an active snapshot ( unless a filter param of live_stock = true say so ).

The return query shape of the endpoint for getting the list of StockReportItems should now bring the snapshot object also, i will update the frontend to consume that later one. 

We will need a new endpoint for allowing the creation of a new snapshot ( creating a new snapshot closes the previous one as mentioned before ), the act of creating a new snapshot creates a snapshot for all the StockReportItems ( make it efficient and atomic ). 

As mentioned previously the missing quantity is a special value which workers or managers  can add, thus we will need a endpoint for allowing this change of missing quantity value on an active snapshot, missing quantity on an active snapshot cannot be < snapshot requested_quantity . 
This missing quantity value will affect the way the default query for StockReportItems behaves, because that query will be returning snapshots where requested_quantity > 0 , but it should actually be = requerted_quantity - quantity_missing > 0  .
On the creation of a new snapshot this missing quantity is not brough from a previous is reseted to 0 because the snapshot quantity_missing defaults the value to 0 on creation, and this is intentional because the manager and workers want to re-asses wheter if ther item is still missing. 
This query endpoint will require a new query param also, so that the user can bring only the stock reports which have an active snapshot with quantity_missing > 0 . This will allow the manager to view re-check for alredy set missing quantity stocks to see if it can find that requested item, and if so register the item to the stock instance ( assign it )

We will need one new endpoint which specializes in getting the quantity_missing. 
One is a counter which gets the count of all the quantity_missing accross all the active snapshots.

as you migh have noticed in my previous description of a manager or worker can see only stocks with missing quantity so that they can try to find one, and if so then they enqueue it ( assign it ), this means that the process of creating an assignment will now get the new responsibility of removing snapshot quantity_missing, if quantity_missing == quantity_requested - quantity_in_queue - quantity_in_progress - quantity_awating . 

The user could also use the same endpoint used to set the missing quantity to remove quantity, but that is a manual approach to that operation. this two ways of decreasing this value have their means of existing. on one ( manual ), this operation is like the manager says to the worker who marked missing "there is, search" . and on the other ( automatic given the business rules ) is like: some one marked missing but then manager found and having it infront assigns it directly. 

I will like you to create a solid plan for implementing this new capability. you can ask me as many questions that are need it, in order to clear any possible issues out of the way. 

Rememeber that for any implementation we choose the correct contracts to follow so that we are align to the architectural contracts, using the guide /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/task_system/backend_contract_goal_mapping_guide.md

