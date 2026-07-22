$content = Get-Content .\pyproject.toml -Raw

# Fix FastAPI version
$content = $content -replace 'fastapi\s*=\s*"[^"]+"', 'fastapi = "0.115.12"'

# Fix Starlette version if explicitly present
if ($content -match 'starlette\s*=') {
    $content = $content -replace 'starlette\s*=\s*"[^"]+"', 'starlette = "0.46.2"'
}
else {
    # Ajoute Starlette après FastAPI dans les dépendances
    $content = $content -replace '(fastapi\s*=\s*"0\.115\.12")', '$1`nstarlette = "0.46.2"'
}

Set-Content .\pyproject.toml $content

Write-Host "pyproject.toml updated successfully"