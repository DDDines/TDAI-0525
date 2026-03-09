from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_production_requirements_exclude_pytest_tooling():
    requirements_path = PROJECT_ROOT / "requirements-backend-prod.txt"
    lines = [
        line.strip()
        for line in requirements_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert "pytest==8.2.1" not in lines
    assert "pytest-asyncio==0.23.6" not in lines
    assert "pytest-cov==7.0.0" not in lines


def test_production_requirements_keep_runtime_packages():
    requirements_path = PROJECT_ROOT / "requirements-backend-prod.txt"
    contents = requirements_path.read_text(encoding="utf-8")

    assert "fastapi==0.110.2" in contents
    assert "celery==5.6.2" in contents
    assert "redis==7.3.0" in contents
    assert "playwright==1.43.0" in contents
