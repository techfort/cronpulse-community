import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models.monitor import Monitor, Base
from db.repositories.monitor_repository import MonitorRepository


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
def monitor_repo(session):
    return MonitorRepository(session)


def test_create_monitor(monitor_repo: MonitorRepository, session):
    monitor = Monitor(name="Test Monitor", interval=10.0, user_id=1)
    monitor_repo.create(monitor)
    found = session.query(Monitor).filter_by(name="Test Monitor").first()
    assert found is not None
    assert found.name == "Test Monitor"
    assert found.interval == 10.0
    assert found.user_id == 1


def test_get_monitor_by_id(monitor_repo, session):
    monitor = Monitor(id=42, name="Monitor42", interval=5.0, user_id=2)
    session.add(monitor)
    session.commit()
    found = monitor_repo.get_by_id(42, user_id=2)
    assert found is not None
    assert found.name == "Monitor42"
    assert found.interval == 5.0
    assert found.user_id == 2


@pytest.mark.parametrize(
    "monitors,user_id,expected_count",
    [
        (
            [
                Monitor(name="M1", interval=1.0, user_id=10),
                Monitor(name="M2", interval=2.0, user_id=10),
                Monitor(name="M3", interval=3.0, user_id=11),
            ],
            10,
            2,
        ),
        (
            [
                Monitor(name="M4", interval=4.0, user_id=12),
            ],
            12,
            1,
        ),
        (
            [],
            15,
            0,
        ),
    ],
)
def test_list_monitors_by_user_parametrized(
    monitor_repo: MonitorRepository, session, monitors, user_id, expected_count
):
    session.add_all(monitors)
    session.commit()
    found = monitor_repo.list_by_user(user_id=user_id)
    assert len(found) == expected_count
    assert all(m.user_id == user_id for m in found)


def test_update_monitor(monitor_repo, session):
    monitor = Monitor(name="Original", interval=10.0, user_id=1)
    session.add(monitor)
    session.commit()
    
    # Update using the actual repository method signature
    monitor.name = "Updated"
    updated = monitor_repo.update(monitor)
    assert updated.name == "Updated"
    assert updated.interval == 10.0


def test_delete_monitor(monitor_repo, session):
    monitor = Monitor(name="ToDelete", interval=5.0, user_id=1)
    session.add(monitor)
    session.commit()
    monitor_id = monitor.id
    
    monitor_repo.delete(monitor_id, user_id=1)
    found = monitor_repo.get_by_id(monitor_id, user_id=1)
    assert found is None
