first i need to create the base for the app true functionality.

we will fist create the routers for working section. 
create working section
edit working section
delete working section
get working section by id
get all working sections

after that we will create the commands for working section.
create working section
edit working section
delete working section
get working section by id
get all working sections

creating a new working section requires: name, image, 
it can include working section dependencies, but it is not required. the working dependecy comes as working_section_dependencies: list of working section ids. the working section item categories can also be included in the create command, the categories come as working_section_item_categories: list of category ids. the working section supported issue types can also be included in the create command, the supported issue types come as working_section_supported_issue_types: list of issue type ids.

it returns only the id of the created working section. ( we still build a serializer to keep the architecture in line with the rest of the app, but it only returns the id for now. )

editing a working section can include changing the name, image, and dependencies. all of these are optional in the edit command, but at least one of them must be included. the edit command requires the id of the working section to be edited. editing the dependencies means replacing all existing dependencies with the new list of dependencies provided in the command. the same applies for the categories and supported issue types, if they are included in the edit command, they will replace all existing categories and supported issue types for that working section.


deleting a working section requires the id of the working section to be deleted.

getting a working section by id requires the id of the working section. 


it returns the id, name, image, and dependencies of the working section. the dependencies are returned as a list of working section ids and section name, it includes the working section item categories and supported issue types, they come as a list of ids and names. we build a serializer for this output as well, to keep the architecture consistent. 

getting all working sections does not require any input. we user the same serializer as the get by id since the output shape is the same.


the query for getting defaults to search for deleted_at = null, so deleted working sections are not returned in the get by id or get all endpoints. we can have a separate endpoint for getting deleted working sections if needed, but for now we will just exclude them from the main endpoints.


any role can access the get endpoints, but only admin can access the create, edit, and delete endpoints. we will enforce this in the router using the current check for role names. 