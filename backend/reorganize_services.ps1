# Services folders

New-Item -ItemType Directory -Force app\services\inventory
New-Item -ItemType Directory -Force app\services\cube
New-Item -ItemType Directory -Force app\services\loan


# Move services

Move-Item app\services\inventory_service.py `
    app\services\inventory\inventory_service.py

Move-Item app\services\cube_completeness_service.py `
    app\services\cube\cube_completeness_service.py

Move-Item app\services\loan_planning_service.py `
    app\services\loan\loan_planning_service.py

Move-Item app\services\loan_session_service.py `
    app\services\loan\loan_session_service.py

Move-Item app\services\loan_session_query_service.py `
    app\services\loan\loan_session_query_service.py

Move-Item app\services\loan_assignment_service.py `
    app\services\loan\loan_assignment_service.py


# Init files

New-Item -ItemType File -Force app\services\inventory\__init__.py
New-Item -ItemType File -Force app\services\cube\__init__.py
New-Item -ItemType File -Force app\services\loan\__init__.py



# Tests folders

New-Item -ItemType Directory -Force tests\inventory
New-Item -ItemType Directory -Force tests\cube
New-Item -ItemType Directory -Force tests\loan


# Move tests

Move-Item tests\test_inventory_service.py `
    tests\inventory\test_inventory_service.py

Move-Item tests\test_cube_completeness_service.py `
    tests\cube\test_cube_completeness_service.py

Move-Item tests\test_loan_planning_service.py `
    tests\loan\test_loan_planning_service.py

Move-Item tests\test_loan_conflict.py `
    tests\loan\test_loan_conflict.py

Move-Item tests\test_loan_session_service.py `
    tests\loan\test_loan_session_service.py

Move-Item tests\test_loan_session_query_service.py `
    tests\loan\test_loan_session_query_service.py

Move-Item tests\test_loan_assignment_service.py `
    tests\loan\test_loan_assignment_service.py