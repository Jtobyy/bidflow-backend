### Commit Structure for Migrations and Code

<type>(<scope>): <message>

Where:

type = what kind of change it is (feature, fix, chore, etc.)

scope = which part of the app (users, tenders, bids, etc.)

message = short, clear description


### Common Types You Should Use

Type	    Meaning	Example
feat	    Adding a new feature	feat(users): add registration model
fix	        Bug fix	fix(bids): correct bid submission bug
chore	    Non-functional changes (e.g., config, deps)	chore: add .env.dev template
refactor	Code structure improvement (no feature)	refactor(users): clean up models
docs	    Documentation changes only	docs(readme): update project setup instructions
test	    Adding or fixing tests	test(users): add unit tests for login
