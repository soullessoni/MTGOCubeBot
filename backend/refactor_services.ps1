New-Item -ItemType Directory -Force app\services\cube | Out-Null
New-Item -ItemType Directory -Force app\services\loan | Out-Null
New-Item -ItemType Directory -Force app\use_cases\loan | Out-Null


# Cube
if (Test-Path app\services\cube_import_service.py) {
    Move-Item `
        app\services\cube_import_service.py `
        app\services\cube\cube_import_service.py
}


# Initialisation des packages
New-Item -ItemType File -Force app\use_cases\__init__.py | Out-Null
New-Item -ItemType File -Force app\use_cases\loan\__init__.py | Out-Null


# Nettoyage pycache éventuels
Get-ChildItem `
    -Path app `
    -Directory `
    -Filter "__pycache__" `
    -Recurse |
    Remove-Item -Recurse -Force