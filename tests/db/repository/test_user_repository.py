import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models.user import User, Base
from db.repositories.user_repository import UserRepository


@pytest.fixture
def session():
    # Create an in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


@pytest.fixture
def user_repo(session) -> UserRepository:
    return UserRepository(session)


def test_create_user(user_repo: UserRepository, session):
    user_repo.create_user(User(email="test@example.com", hashed_password="hashed"))
    found = session.query(User).filter_by(email="test@example.com").first()
    assert found is not None
    assert found.email == "test@example.com"


def test_get_user_by_email(user_repo: UserRepository, session):
    user = User(email="findme@example.com", hashed_password="hashed")
    session.add(user)
    session.commit()
    found = user_repo.get_user_by_email("findme@example.com")
    assert found.email == "findme@example.com"


def test_get_user_by_id(user_repo: UserRepository, session):
    user = User(id=42, email="iduser@example.com", hashed_password="hashed")
    session.add(user)
    session.commit()
    found = user_repo.get_user_by_id(42)
    assert found.email == "iduser@example.com"


def test_get_user_by_email_not_found(user_repo: UserRepository):
    found = user_repo.get_user_by_email("doesnotexist@example.com")
    assert found is None


def test_get_user_by_id_not_found(user_repo: UserRepository):
    found = user_repo.get_user_by_id(999)
    assert found is None
