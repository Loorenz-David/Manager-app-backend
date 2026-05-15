a user can only be registered by an admin user, so there is no public registration endpoint. the admin user can create a new user by providing the user's email, username, role, working sections, password .

the incoming working sections are a list of working section ids, the command will validate that these working section ids exist and are not deleted before creating the user. if any of the provided working section ids are invalid, the command will raise an error and the user will not be created.

the incoming role must be one of the predefined roles in the system, if the provided role is not valid, the command will raise an error and the user will not be created.


optional fields are phone_number, languages ( coming as a list of languages ), languages_preference, single string

the languages is made a single string coma separated 

the command should create a new user record in the database with the provided information, and also create the necessary relationships with the working sections and role. 

the command should return the id of the newly created user.