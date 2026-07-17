# MTGOCubeBot - Initial project structure

Write-Host "Creating MTGOCubeBot structure..."

# Backend folders
$folders = @(
    "backend",
    "backend\app",
    "backend\app\api",
    "backend\app\core",
    "backend\app\db",
    "backend\app\models",
    "backend\app\schemas",
    "backend\app\services",
    "backend\app\utils",
    "backend\tests",
    "backend\alembic",
    "agent",
    "docs"
)

foreach ($folder in $folders) {
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
    Write-Host "Created $folder"
}


# Python init files
$pythonFiles = @(
    "backend\app\__init__.py",
    "backend\app\api\__init__.py",
    "backend\app\core\__init__.py",
    "backend\app\db\__init__.py",
    "backend\app\models\__init__.py",
    "backend\app\schemas\__init__.py",
    "backend\app\services\__init__.py",
    "backend\app\utils\__init__.py"
)

foreach ($file in $pythonFiles) {
    New-Item -ItemType File -Force -Path $file | Out-Null
    Write-Host "Created $file"
}


# Basic README files
New-Item -ItemType File -Force -Path "README.md" | Out-Null
New-Item -ItemType File -Force -Path "backend\README.md" | Out-Null
New-Item -ItemType File -Force -Path "agent\README.md" | Out-Null
New-Item -ItemType File -Force -Path "docs\architecture.md" | Out-Null


Write-Host ""
Write-Host "Structure created successfully."