from Backend.main import create_new_user
import Backend.schemas as schemas


def test_user_registration(db_session):
    user_in = schemas.UserCreate(
        email="test@example.com",
        password="secret",
        nome_completo="Test User",
    )
    new_user = create_new_user(user_in=user_in, db=db_session)
    assert new_user.email == user_in.email
    assert new_user.id is not None
