we will now create the atomic commands for creating and item

creating and item creates an item instance,
item mandatory fields: article_number or sku, item_category_id ( we must verify it before appending it  ), quanity ( if missing defaults to 1 ).

the incoming payload can bring item_issues which is a list of objects with keys issue_type_id, issue_severity_id, base_time_seconds, time_mulitplier, issue_name_snapshot, severity_name_snapshot,

the issue_type_id and issue_severity_id can be missing, or null, because the user can create an issue for an item directly to the item and still not have it exist in the stored item issues ( i will later resolve the way this issues created with out issue type link andseverity link will move to created in record )

the incoming issues can also be missing or null at base_time_seconds, time_multiplier, and severity_name_snapshot. so an incoming issue can only have the issue_name_snapshot and still be valid for creation, and in that case the created item issue will have null for the missing fields.


an item can bring the key item_upholsterie which is an object. we use the atomic command that alredy exists for creating and item upholstery instance linked to the item currently getting created. 
the object comes with keys: upholstery_id, source, name, code, amount_meters. 

the source can come as costumer, in which case it will not include the upholstery_id, but then the name and code are mandatory.

when passing the source internal, upholstery_id must be present and the name, code can be missing from the payload because we can get those from the upholstery registry based on the upholstery_id

amount_meters can be missing or null, the creation of item upholstery command already accounts for this. 

time_to_fic_in_seconds is a value that also can be missing.


the creation of issues on an item is it's own atomic command as i plan to use that command for creating item issues individually or as part of other higher commands

the default state of an item on creation is pending. 

the other fields of the item can be present but are not mandatory 


we will need a command for updating an item, this command will update only the item columns,

the other tables like item issue and item upholstery will have or already their own update commands

deleting and item uses the soft delete patterns, 

getting an item has the common command pattern we have stablish, list of item which accepts a query with filters "q" and pagination, and get item by id which accepts the item client_id as path parameter and returns the item with its linked item issues and item upholstery if they exist.





item has a serializer that returns the: id, article_number, sku, state, item_category: {id, name, major category name}, quantity, height_in_cm, width_in_cm, length_in_cm, item_value_minor, item_currency, item_position, external_id, external_url, external_source, external_order_id, created_at,created_by. if the item is of major category "seat" then it will include the key item_upholstery which is an object of the item upholstery serializer, if not it will not include the key item_upholstery. it will also use the item issue serializer to serialize the item issues list if it exists, if not it will return an empty list for item issues.




item upholstery has a serializers that returns the item upholstery:id , item_id, upholstery_id, name,code, amount_meters, source, time_ro_fix_in_seconds, active_requirement_id, created_at, created_by_id. it also includes the key item_upholstery_requirements which is a list of objects of the ItemUpholsteryRequirements serialized 

the item upholstery requirements has a serializer that returns the id, item_upholstery_id, upholstery_inventory_id, amount_meters, value_minor, currency, source, state, ordered_at, in_use_at, completed_at, failed_at, updated_at, updated_by_id,


item issues seriolizer returns the id, issue_type_id, issue_severity_id, base_time_seconds, time_mulitplier, issue_name_snapshot, severity_name_snapshot, created_at, created_by_id, updated_at, updated_by_id