at the tasks router we are missing to create the routes and the service for getting the history records of a task, this return will be actually a mix of mutliple history records and events, as this return will be actaully more of a task flow record. the shapes returnd should be normilized to a standar object that the fronent can read reliably and ask for more details if need it. we will paginate by 10 records and so far we won't have query params, the list should be orderd by date ( most recent at the top ) . 

the standarized shape: 
{ 
    type: history_record | event | task_step,
    entity_type: item | item_upholstery_requirement | item_upholstery | case | task | other we can think of in the future,
    entity_client_id: string,
    description: string,
    created_at: datetime,
    created_by: {
        client_id: string,
        username: string,
        profile_picture: string
    },

 }

 we will extract the task history record from the polymorphic system.

 we will extract the item upholstery requirement hisotry from the polymorphic system as well, this will be a history record with entity_type = item_upholstery_requirement 

we will extract the item upholstery history from the polymorphic system as well, this will be a history record with entity_type = item_upholstery

we will extract the case history from the polymorphic system as well, this will be a history record with entity_type = case


 we will also extract the task step records,  mapping created_at and created_by to the user and time of creation. enitty_client_id will be the task step client id and description will be formated to be: "{username} marked {state} on working section{working_section_name}"


the pagination should limit to 10 records and we should order by created_at desc, we can also add a has_more boolean in the response to indicate if there are more records to fetch.
