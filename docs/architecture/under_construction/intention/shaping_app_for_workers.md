now im building the worker app at the frontend and the backend is needing to build some logic to please the frontend. this is the get  user working sections with steps state counts  and the get  working section setps . the get worker working sections is a router which will take the user and return the current working sections the user is assigned to 

serializer:
[{working_section_id, working_section_name, , image,  task_steps_counts: {}}]. 
it will also return the task step state counts for that working section, so task_steps_counts: { pending: int .... } . this return states are pending, working, paused, ended_shift, blocked , that is an overall task step query ( narrow by working section id ). it will also return some of the terminal states but only for those that where marked today ( current user date ), those states are: completed, skipped, failed . perhaps for those the #sym:latest_state_record  can be joined and checked on the current user start of date > ( if that is efficient ).  


for the get  working section steps it takes  the working section id, it returns all the steps for that working section, 

that task step serializer:{

    client_id,
    state,
    readiness_status,
    working_section_id,
    assigned_worker_id,
    total_dependencies,
    completed_dependencies,
    created_at,
    created_by:{serialize_user_working_section_member},
    updated_at,
    last_state_record:{ state record step light serialization},

    task:{task light serialization}
    item:{item light serialization}
    item_images:[item_image_serializer]
}

state record step light serialization is :{
    state,
    entered_at,
    exited_at,
}

for the user serializations i already have a serializer with that shape that can be used, called: #sym:serialize_user_working_section_member  ( /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/domain/users/serializers.py )

task light serialization is :{
    client_id,
    task_type,
    priority,
    state,
    return_source,
    item_location,
    ready_by_at,
    return_method
}

item light serialization is :{
    client_id,
    article_number,
    sku,
    state,
    item_category_id,
    quantity,
    item_position,
    item_upholstery_id,
    upholstery_requirement ( if the item has upholstery in ItemUpholstery ):[{state, client_id, source, amount_meters}]
}

item images serialization is we use same strategy as tasks query service "image_list.append(serialize_image(image) if not image_list else serialize_image_light(image))" at  /Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app/backend/app/beyo_manager/services/queries/tasks/tasks.py, 

this working section steps router accepts a query param called "q" , the query list service uses the same strategy as other services using the "q" param, this string search is against the item article number and sku, upholstery name  upholstery code . 
the difference in this search is that as default the "q" will always search agains article number and sky, and only if frontend sends paraam "upholstery_search" as true then the search will also include upholstery name and code.


i will like you to create a implementation plan 








