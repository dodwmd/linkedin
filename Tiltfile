# Define the Docker build
docker_build(
    'app_app',  # This should match the service name in docker-compose.yml
    '.',
    dockerfile='Dockerfile',
    ignore=[
        'Tiltfile',
        '.git',
        '.gitignore',
        'README.md',
        'docker-compose.yml',
        '.env',
        '.env.example',
        '**/__pycache__',
        '**/*.pyc',
        '**/*.pyo',
        '**/*.pyd',
        '.pytest_cache',
        '.mypy_cache',
        '.vscode',
        '.idea',
    ],
    live_update=[
        sync('src', '/app/src'),
        sync('linkedin_scraper', '/app/linkedin_scraper'),
        run('pip install -r requirements.txt', trigger='requirements.txt'),
    ]
)

# Use docker-compose for local development
docker_compose('docker-compose.yml')

# Custom function to run pytest
def run_tests():
    local_resource(
        'run-tests',
        cmd='docker compose exec -e TESTING=1 -w /app app pytest src/tests',
        auto_init=False,
        trigger_mode=TRIGGER_MODE_MANUAL
    )

# Custom function to run linter
def run_linter():
    local_resource(
        'run-linter',
        cmd='docker compose exec -w /app app flake8 src',
        auto_init=False,
        trigger_mode=TRIGGER_MODE_MANUAL
    )

# Custom function to run type checker
def run_type_checker():
    local_resource(
        'run-type-checker',
        cmd='docker compose exec -w /app app mypy src',
        auto_init=False,
        trigger_mode=TRIGGER_MODE_MANUAL
    )

# Watch specific files and directories
watch_file('src')
watch_file('linkedin_scraper')
watch_file('requirements.txt')

# Define a custom build step that runs tests, linter, and type checker
local_resource(
    'run-checks',
    cmd='docker compose exec -e TESTING=1 -w /app app sh -c "pytest src/tests && flake8 src && mypy src"',
    deps=['src', 'linkedin_scraper'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_MANUAL
)

# Add custom buttons to Tilt UI (using local_resource instead of cmd_button)
run_tests()
run_linter()
run_type_checker()

# Enable hot reloading for the Flask app
dc_resource('app', trigger_mode=TRIGGER_MODE_AUTO)

# Add a new local_resource for linting
local_resource(
    'lint-check',
    cmd='docker compose exec -w /app app flake8 src',
    deps=['src'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_AUTO
)

# Add a new local_resource for type checking
local_resource(
    'type-check',
    cmd='docker compose exec -w /app app mypy src',
    deps=['src'],
    auto_init=False,
    trigger_mode=TRIGGER_MODE_AUTO
)

update_settings(max_parallel_updates=3)
