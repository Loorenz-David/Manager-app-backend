the current roles stablish are the vanilla roles comming from the bootstrap.

we will be making some basic changes to this roles, we will keep ADMIN, we will remove the MEMEBER and FIELD. we will add WORKER, MANAGER, SELLER.

we will create a bootstrap router, command, which will serve as the initial app build data seeding point. in this router we will create the new roles and assign them to the default admin user. 

we will also create a default user on this bootstrap, the users info will be taken from the env variables, this default user will be assigned the admin role, this is to ensure that we have a user with the correct permissions to access the app after the initial build.

this bootstrap router and command will be idempotent, so it can be safely re-run if needed without creating duplicates or causing errors. we will use the same pattern as the identity bootstrap for this, with a check for existing data before attempting to create new records.

i want the commands build for this bootstrap to be scalable so that as i build the rest of the app, if i need to add more default data to be seeded on the initial build, i can easily add it to this bootstrap without having to worry about the idempotency or the order of execution.
