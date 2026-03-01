from Backend.main import MainBootstrapWorkflow
import Backend.schemas as schemas


class _TopLevelFunctionSurface:

    def test_user_registration(db_session):
        user_in = schemas.UserCreate(
            email="test@example.com",
            password="secret",
            nome_completo="Test User",
        )
        new_user = MainBootstrapWorkflow().create_new_user(user_in=user_in, session=db_session)
        assert new_user.email == user_in.email
        assert new_user.id is not None

test_user_registration = _TopLevelFunctionSurface.test_user_registration

